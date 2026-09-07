import {Fragment, useDeferredValue, useEffect, useMemo, useRef, useState} from 'react';
import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import Layout from '@theme/Layout';
import snapshotData from '@site/src/data/api-reference.json';
import {catalogOperations, collectReferences, describeSchema, filterOperations, HTTP_METHODS, resolveReference, schemaNameFromReference, validateOpenApi} from '@site/src/lib/openapi.mjs';
import styles from './api-reference.module.css';

type JsonObject = Record<string, any>;
type Operation = ReturnType<typeof catalogOperations>[number];
type Snapshot = {
  status: string;
  version: string;
  schemaPath: string;
  sourceRepository: string;
  license: string;
  attribution: string;
  generatedAt?: string;
  sourceRevision?: string;
  sha256?: string;
  bytes?: number;
  omittedPrivateDefaults?: number;
  omissions?: {path: string; method: string; parameter: string}[];
  wheelSha256?: string;
  capture?: string;
  counts?: {paths: number; operations: number; schemas: number};
};
const snapshot: Snapshot = snapshotData;
const PAGE_SIZE = 25;

function RawDefinition({value, label = 'Complete definition'}: {value: unknown; label?: string}) {
  return <details className={styles.raw}><summary>{label}</summary><pre><code>{JSON.stringify(value, null, 2)}</code></pre></details>;
}

function SchemaSummary({schema, onSchema}: {schema?: JsonObject | boolean; onSchema: (name: string) => void}) {
  const references = collectReferences(schema).map(schemaNameFromReference).filter((name): name is string => name !== null);
  return <div className={styles.schemaSummary}>
    <code>{describeSchema(schema)}</code>
    {references.length > 0 && <div className={styles.references}>Models: {[...new Set(references)].map((name) =>
      <button key={name} type="button" onClick={() => onSchema(name)}>{name}</button>,
    )}</div>}
  </div>;
}

function resolved(document: JsonObject, value: JsonObject): JsonObject {
  return value?.$ref ? resolveReference(document, value.$ref) : value;
}

function ContentSchemas({content, onSchema}: {content?: JsonObject; onSchema: (name: string) => void}) {
  if (!content || !Object.keys(content).length) return <span>No response/request media type declared.</span>;
  return <>{Object.entries(content).map(([mediaType, media]) => <div className={styles.media} key={mediaType}>
    <strong>{mediaType}</strong>
    <SchemaSummary schema={media.schema} onSchema={onSchema} />
    {(media.example !== undefined || media.examples !== undefined) &&
      <RawDefinition label="Examples declared in the schema" value={media.examples ?? media.example} />}
  </div>)}</>;
}

function OperationDetails({entry, document, onSchema}: {entry: Operation; document: JsonObject; onSchema: (name: string) => void}) {
  const parameters = new Map<string, JsonObject>();
  for (const source of entry.parameters) {
    const parameter = resolved(document, source);
    parameters.set(`${parameter.in}:${parameter.name}`, parameter);
  }
  const requestBody = entry.operation.requestBody ? resolved(document, entry.operation.requestBody) : null;
  return <div className={styles.operationDetails}>
    <p><strong>Operation ID:</strong> <code>{entry.id}</code></p>
    {entry.description && <p className={styles.description}>{entry.description}</p>}
    {entry.deprecated && <p className={styles.warning}>Deprecated in the captured schema. Check the installed API for its replacement.</p>}
    <h3>Authentication declaration</h3>
    {entry.security === undefined ? <p>No security requirement declared here. Runtime authentication and authorization may still apply; this is not a claim of public access.</p>
      : entry.security.length === 0 ? <p>The schema declares an empty security requirement. Runtime route policy remains authoritative.</p>
        : <><p>The schema declares these alternative security requirements. Requirements within one object apply together.</p><RawDefinition label="Security requirements" value={entry.security} /></>}
    <h3>Parameters</h3>
    {!parameters.size ? <p>No path, query, header, or cookie parameters declared.</p> : <div className={styles.tableScroll}>
      <table className={styles.detailTable}>
        <thead><tr><th scope="col">Name / location</th><th scope="col">Requirement / schema</th><th scope="col">Description</th></tr></thead>
        <tbody>{[...parameters.values()].map((parameter) => <tr key={`${parameter.in}:${parameter.name}`}>
          <th scope="row"><code>{parameter.name}</code><br /><small>{parameter.in}</small></th>
          <td><span>{parameter.required ? 'Required' : 'Optional'}</span><SchemaSummary schema={parameter.schema} onSchema={onSchema} />
            {parameter.schema && Object.hasOwn(parameter.schema, 'default') && <div>Default: <code>{JSON.stringify(parameter.schema.default)}</code></div>}
          </td>
          <td className={styles.description}>{parameter.description ?? 'No description declared.'}</td>
        </tr>)}</tbody>
      </table>
    </div>}
    <h3>Request body</h3>
    {requestBody ? <><p>{requestBody.required ? 'Required' : 'Optional'}{requestBody.description ? ` — ${requestBody.description}` : ''}</p><ContentSchemas content={requestBody.content} onSchema={onSchema} /></>
      : <p>No request body declared.</p>}
    <h3>Responses</h3>
    <div className={styles.tableScroll}><table className={styles.detailTable}>
      <thead><tr><th scope="col">Status</th><th scope="col">Description and media types</th></tr></thead>
      <tbody>{Object.entries(entry.operation.responses ?? {}).map(([status, value]) => {
        const response = resolved(document, value as JsonObject);
        return <tr key={status}><th scope="row"><code>{status}</code></th><td><p className={styles.description}>{response.description}</p>
          <ContentSchemas content={response.content} onSchema={onSchema} />
          {response.headers && <RawDefinition label="Response headers" value={response.headers} />}
          {response.links && <RawDefinition label="Response links" value={response.links} />}
        </td></tr>;
      })}</tbody>
    </table></div>
    <RawDefinition value={entry.operation} label="Complete operation JSON (including extensions and examples)" />
  </div>;
}

function Pagination({page, count, onChange, label}: {page: number; count: number; onChange: (page: number) => void; label: string}) {
  const pages = Math.max(1, Math.ceil(count / PAGE_SIZE));
  return <nav className={styles.pagination} aria-label={`${label} pagination`}>
    <button className="button button--secondary button--sm" type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
    <span>Page {page} of {pages}</span>
    <button className="button button--secondary button--sm" type="button" disabled={page >= pages} onClick={() => onChange(page + 1)}>Next</button>
  </nav>;
}

function ModelDefinition({name, document, onSchema}: {name: string; document: JsonObject; onSchema: (name: string) => void}) {
  const schema = document.components?.schemas?.[name];
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {heading.current?.focus();}, [name]);
  if (schema === undefined) return null;
  return <section className={styles.modelDetail} aria-label={`Schema ${name}`}>
    <h2 ref={heading} tabIndex={-1}>{name}</h2>
    <SchemaSummary schema={schema} onSchema={onSchema} />
    {schema.description && <p className={styles.description}>{schema.description}</p>}
    {schema.enum && <p>Allowed values: <code>{JSON.stringify(schema.enum)}</code></p>}
    {schema.properties && <div className={styles.tableScroll}><table className={styles.detailTable}>
      <thead><tr><th scope="col">Property</th><th scope="col">Schema / required</th><th scope="col">Description / default</th></tr></thead>
      <tbody>{Object.entries(schema.properties).map(([property, definition]) => {
        const field = definition as JsonObject;
        return <tr key={property}><th scope="row"><code>{property}</code></th>
          <td><SchemaSummary schema={field} onSchema={onSchema} /><span>{schema.required?.includes(property) ? 'Required' : 'Optional'}</span></td>
          <td className={styles.description}>{field.description ?? ''}
            {Object.hasOwn(field, 'default') && <div>Default: <code>{JSON.stringify(field.default)}</code></div>}
            {field.enum && <div>Allowed: <code>{JSON.stringify(field.enum)}</code></div>}
          </td>
        </tr>;
      })}</tbody>
    </table></div>}
    <RawDefinition value={schema} label="Complete model JSON (constraints, unions, defaults, and examples)" />
  </section>;
}

export default function ApiReference(): ReactNode {
  const schemaUrl = useBaseUrl(snapshot.schemaPath);
  const [document, setDocument] = useState<JsonObject | null>(null);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  const [tab, setTab] = useState<'operations' | 'schemas'>('operations');
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const [method, setMethod] = useState('');
  const [tag, setTag] = useState('');
  const [page, setPage] = useState(1);
  const [selectedOperation, setSelectedOperation] = useState('');
  const [schemaQuery, setSchemaQuery] = useState('');
  const [schemaPage, setSchemaPage] = useState(1);
  const [selectedSchema, setSelectedSchema] = useState('');

  useEffect(() => {
    if (snapshot.status !== 'ready') return;
    const controller = new AbortController();
    setError('');
    async function load() {
      const response = await fetch(`${schemaUrl}?sha256=${snapshot.sha256}`, {signal: controller.signal, credentials: 'omit'});
      if (!response.ok) throw new Error(`Schema download returned HTTP ${response.status}.`);
      const bytes = await response.arrayBuffer();
      const digest = await crypto.subtle.digest('SHA-256', bytes);
      const hash = [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, '0')).join('');
      if (hash !== snapshot.sha256) throw new Error('The downloaded schema does not match this page’s recorded SHA-256. Refresh after deployment completes.');
      const data = JSON.parse(new TextDecoder().decode(bytes));
      validateOpenApi(data, snapshot.version);
      if (!controller.signal.aborted) setDocument(data);
    }
    load().catch((failure) => {if (!controller.signal.aborted) setError(failure instanceof Error ? failure.message : 'Unable to load the schema.');});
    return () => controller.abort();
  }, [schemaUrl, retry]);

  const operations = useMemo(() => document ? catalogOperations(document) : [], [document]);
  const tags = useMemo(() => [...new Set(operations.flatMap((operation) => operation.tags))].sort() as string[], [operations]);
  const filtered = useMemo(() => filterOperations(operations, deferredQuery, method, tag), [operations, deferredQuery, method, tag]);
  const currentPage = Math.min(page, Math.max(1, Math.ceil(filtered.length / PAGE_SIZE)));
  const schemas = useMemo(() => Object.keys(document?.components?.schemas ?? {}).sort(), [document]);
  const filteredSchemas = useMemo(() => schemas.filter((name) => name.toLowerCase().includes(schemaQuery.trim().toLowerCase())), [schemas, schemaQuery]);
  const currentSchemaPage = Math.min(schemaPage, Math.max(1, Math.ceil(filteredSchemas.length / PAGE_SIZE)));

  useEffect(() => {
    if (!document) return;
    const params = new URLSearchParams(window.location.search);
    const operationId = params.get('operation');
    const schemaName = params.get('schema');
    const index = operations.findIndex((operation) => operation.id === operationId);
    if (index >= 0) {
      setSelectedOperation(operationId!);
      setPage(Math.floor(index / PAGE_SIZE) + 1);
    } else if (schemaName && schemas.includes(schemaName)) {
      setTab('schemas');
      setSelectedSchema(schemaName);
      setSchemaPage(Math.floor(schemas.indexOf(schemaName) / PAGE_SIZE) + 1);
    }
  }, [document, operations, schemas]);

  function updateUrl(key: string, value: string) {
    const url = new URL(window.location.href);
    url.searchParams.delete('operation');
    url.searchParams.delete('schema');
    if (value) url.searchParams.set(key, value);
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
  }
  function openSchema(name: string) {
    setTab('schemas');
    setSelectedSchema(name);
    setSchemaQuery('');
    setSchemaPage(Math.floor(schemas.indexOf(name) / PAGE_SIZE) + 1);
    updateUrl('schema', name);
  }
  function clearFilters() {setQuery(''); setMethod(''); setTag(''); setPage(1);}

  return <Layout title="API reference & schema catalog" description="Search the captured installed Studio API by HTTP method, path, summary, or tag. Inspect request and response models and download the complete validated OpenAPI document.">
    <main className={`container ${styles.page}`}>
      <header className={styles.header}>
        <span className="status-badge">Installed application schema · Python {snapshot.version}</span>
        <h1>API reference & schema catalog</h1>
        <p className={styles.intro}>Browse the actual Studio application contract—not a hand-written list of guessed endpoints. Filtering and model inspection run locally in your browser. This page never sends requests to a Studio instance.</p>
        <p><Link to="/docs/api">API setup & authentication</Link> · <Link to="/docs/mcp">MCP integration</Link> · <Link to="/docs/security">Deployment security</Link></p>
      </header>
      {snapshot.status !== 'ready' ? <section className={styles.notice}>
        <h2>Awaiting the regenerated installed-app schema</h2>
        <p>The reference will be enabled after the rebuilt package’s OpenAPI document passes operation-ID, local-reference, version, and privacy checks. The older duplicate-ID snapshot is deliberately not published, rewritten, or offered for download.</p>
        <p>The <Link to="/docs/api">source-verified API guide</Link> remains available. Schema availability is independent of desktop release qualification.</p>
      </section> : <>
        <section className={styles.notice} aria-label="Snapshot provenance">
          <div className={styles.snapshotHeading}>
            <div><h2>{snapshot.counts?.operations} operations · {snapshot.counts?.paths} paths · {snapshot.counts?.schemas} models</h2>
              <p>Captured <time dateTime={snapshot.generatedAt}>{snapshot.generatedAt}</time> from the installed package.</p>
            </div>
            <a className="button button--primary" href={schemaUrl} download="darbot-unsloth-openapi.json">Download complete OpenAPI JSON</a>
          </div>
          <p><strong>Privacy disclosure:</strong> {snapshot.omittedPrivateDefaults} environment-local directory query defaults were omitted. All operations and model definitions are retained; this catalog does not remove endpoints, shorten the download, or rewrite operation IDs.</p>
          <p><strong>Scope:</strong> this is the application’s OpenAPI schema. Mounted MCP tools and protocol methods are not an OpenAPI operation inventory. Absence of a security declaration does not bypass runtime authorization, and schema capture does not certify every model or backend.</p>
          <details><summary>Checksum, source provenance, and license</summary>
            <p>SHA-256: <code className={styles.break}>{snapshot.sha256}</code><br />Size: {snapshot.bytes?.toLocaleString('en-US')} bytes</p>
            {snapshot.capture && <p>Capture scope: {snapshot.capture}.</p>}
            {snapshot.wheelSha256 && <p>Installed wheel SHA-256: <code className={styles.break}>{snapshot.wheelSha256}</code></p>}
            <p>Source revision: <a href={`${snapshot.sourceRepository}/commit/${snapshot.sourceRevision}`}>{snapshot.sourceRevision}</a></p>
            {snapshot.omissions && <><p>Only the defaults at these optional query parameters were omitted; the parameters themselves remain in the schema:</p>
              <ul>{snapshot.omissions.map((omission) => <li key={`${omission.path}:${omission.parameter}`}><code>{omission.method.toUpperCase()} {omission.path}</code> — <code>{omission.parameter}</code></li>)}</ul>
            </>}
            <p>{snapshot.attribution} The generated schema retains <a href={`${snapshot.sourceRepository}/blob/${snapshot.sourceRevision}/studio/LICENSE.AGPL-3.0`}>{snapshot.license}</a>; the website’s Apache-2.0 label does not relicense it.</p>
          </details>
        </section>
        {error ? <div role="alert" className={styles.notice}><h2>Schema could not be loaded</h2><p>{error}</p><button className="button button--secondary" type="button" onClick={() => setRetry((value) => value + 1)}>Retry schema download</button></div>
          : !document ? <p role="status">Loading and verifying the complete local schema…</p>
            : <>
              <div className={styles.tabs} aria-label="Reference views">
                <button className={`button ${tab === 'operations' ? 'button--primary' : 'button--secondary'}`} type="button" aria-pressed={tab === 'operations'} onClick={() => {setTab('operations'); updateUrl('', '');}}>Operations ({operations.length})</button>
                <button className={`button ${tab === 'schemas' ? 'button--primary' : 'button--secondary'}`} type="button" aria-pressed={tab === 'schemas'} onClick={() => {setTab('schemas'); updateUrl('', '');}}>Models ({schemas.length})</button>
              </div>
              {tab === 'operations' ? <section aria-label="Operation catalog">
                <div className={styles.filters}>
                  <label>Search method, path, summary, description, or ID<input type="search" value={query} placeholder="For example: train status" onChange={(event) => {setQuery(event.target.value); setPage(1);}} /></label>
                  <label>Method<select value={method} onChange={(event) => {setMethod(event.target.value); setPage(1);}}><option value="">All methods</option>{HTTP_METHODS.map((value) => <option key={value} value={value.toUpperCase()}>{value.toUpperCase()}</option>)}</select></label>
                  <label>Tag<select value={tag} onChange={(event) => {setTag(event.target.value); setPage(1);}}><option value="">All tags</option>{tags.map((value) => <option key={value}>{value}</option>)}</select></label>
                  <button type="button" className="button button--secondary" onClick={clearFilters}>Clear filters</button>
                </div>
                <p role="status" aria-live="polite">{filtered.length} of {operations.length} operations match. Showing {PAGE_SIZE} per page.</p>
                <Pagination page={currentPage} count={filtered.length} onChange={setPage} label="Operations" />
                {!filtered.length ? <p className={styles.notice}>No matching operations. Try a shorter query or clear the method/tag filters.</p> :
                  <div className={styles.tableScroll}><table className={styles.operations}>
                    <caption className={styles.caption}>Select an operation to inspect its declared contract. The address bar retains a shareable operation selection.</caption>
                    <thead><tr><th scope="col">Method</th><th scope="col">Path / summary</th><th scope="col">Tags</th></tr></thead>
                    <tbody>{filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE).map((entry) => <Fragment key={entry.id}>
                      <tr className={selectedOperation === entry.id ? styles.selected : undefined}>
                        <td><span className={styles.method} data-method={entry.method}>{entry.method}</span></td>
                        <th scope="row"><button className={styles.pathButton} type="button" aria-expanded={selectedOperation === entry.id} aria-controls={selectedOperation === entry.id ? `detail-${entry.id}` : undefined} onClick={() => {
                          const next = selectedOperation === entry.id ? '' : entry.id;
                          setSelectedOperation(next); updateUrl('operation', next);
                        }}><code>{entry.path}</code></button><div className={styles.summary}>{entry.summary}{entry.deprecated && ' · Deprecated'}</div></th>
                        <td>{entry.tags.join(', ')}</td>
                      </tr>
                      {selectedOperation === entry.id && <tr id={`detail-${entry.id}`}><td colSpan={3}><OperationDetails entry={entry} document={document} onSchema={openSchema} /></td></tr>}
                    </Fragment>)}</tbody>
                  </table></div>}
                <Pagination page={currentPage} count={filtered.length} onChange={setPage} label="Operations bottom" />
              </section> : <section aria-label="Model catalog">
                <label className={styles.schemaFilter}>Find a model definition<input type="search" value={schemaQuery} placeholder="For example: TrainingStartRequest" onChange={(event) => {setSchemaQuery(event.target.value); setSchemaPage(1);}} /></label>
                <p role="status" aria-live="polite">{filteredSchemas.length} of {schemas.length} model definitions match.</p>
                <Pagination page={currentSchemaPage} count={filteredSchemas.length} onChange={setSchemaPage} label="Models" />
                <div className={styles.modelList}>{filteredSchemas.slice((currentSchemaPage - 1) * PAGE_SIZE, currentSchemaPage * PAGE_SIZE).map((name) =>
                  <button className={name === selectedSchema ? styles.activeModel : ''} key={name} type="button" onClick={() => {setSelectedSchema(name); updateUrl('schema', name);}}>{name}</button>,
                )}</div>
                {!filteredSchemas.length && <p className={styles.notice}>No matching model definitions.</p>}
                {selectedSchema ? <ModelDefinition name={selectedSchema} document={document} onSchema={openSchema} /> : <p>Select a model to inspect fields, required properties, references, constraints, and its complete JSON definition.</p>}
              </section>}
              <details className={styles.raw}><summary>Document-level security schemes</summary><p>These are schema declarations, not a complete account of runtime authorization.</p><pre><code>{JSON.stringify(document.components?.securitySchemes ?? {}, null, 2)}</code></pre></details>
            </>}
      </>}
      <footer className={styles.notes}>
        <h2>Reading this reference</h2>
        <p>Summary tables expose common OpenAPI fields. Expand complete definitions or download the JSON for exact unions, constraints, extensions, examples, response headers, and less common fields. Parameters declared on a path are inherited; operation-level parameters override a matching name/location pair.</p>
        <p>A schema snapshot describes its captured installed version, not necessarily the instance you are running. Inspect that instance’s <code>/openapi.json</code> when versions differ. This is a read-only documentation catalog: it has no token storage, “try it” request runner, or external Swagger/Redoc/CDN dependency.</p>
        <p><Link to="/docs/api">Read the API integration guide</Link> · <Link to="/docs/support">Qualification boundaries</Link> · <Link to="/docs/licenses">Attribution and licenses</Link></p>
      </footer>
    </main>
  </Layout>;
}
