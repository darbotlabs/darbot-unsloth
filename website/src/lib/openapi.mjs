export const HTTP_METHODS = ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace'];

/** @param {Record<string, any>} document */
export function catalogOperations(document) {
  return Object.entries(document.paths ?? {}).flatMap(([path, item]) =>
    HTTP_METHODS.filter((method) => item[method]).map((method) => {
      const operation = item[method];
      return {
        path,
        method: method.toUpperCase(),
        id: operation.operationId,
        summary: operation.summary ?? '',
        description: operation.description ?? '',
        tags: operation.tags?.length ? operation.tags : ['Untagged'],
        deprecated: operation.deprecated === true,
        parameters: [...(item.parameters ?? []), ...(operation.parameters ?? [])],
        security: Object.hasOwn(operation, 'security') ? operation.security : document.security,
        operation,
      };
    }),
  ).sort((a, b) => a.path.localeCompare(b.path, 'en') || HTTP_METHODS.indexOf(a.method.toLowerCase()) - HTTP_METHODS.indexOf(b.method.toLowerCase()));
}

/** @param {ReturnType<typeof catalogOperations>} operations */
export function filterOperations(operations, query = '', method = '', tag = '') {
  const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
  return operations.filter((operation) => {
    if (method && operation.method !== method) return false;
    if (tag && !operation.tags.includes(tag)) return false;
    const text = [operation.path, operation.method, operation.id, operation.summary, operation.description, ...operation.tags].join(' ').toLowerCase();
    return terms.every((term) => text.includes(term));
  });
}

/** @param {unknown} value */
export function collectReferences(value) {
  const refs = new Set();
  function visit(node) {
    if (!node || typeof node !== 'object') return;
    if (typeof node.$ref === 'string') refs.add(node.$ref);
    for (const child of Object.values(node)) visit(child);
  }
  visit(value);
  return [...refs];
}

/** @param {Record<string, any>} document @param {string} reference */
export function resolveReference(document, reference) {
  if (!reference.startsWith('#')) throw new Error(`External reference is not a bundled local reference: ${reference}`);
  const pointer = decodeURIComponent(reference.slice(1));
  if (pointer === '') return document;
  if (!pointer.startsWith('/')) throw new Error(`Unsupported local reference: ${reference}`);
  let current = document;
  for (const raw of pointer.slice(1).split('/')) {
    if (/~(?![01])/u.test(raw)) throw new Error(`Invalid JSON pointer escape: ${reference}`);
    const key = raw.replace(/~1/g, '/').replace(/~0/g, '~');
    if (!current || typeof current !== 'object' || !Object.hasOwn(current, key)) {
      throw new Error(`Unresolved local reference: ${reference}`);
    }
    current = current[key];
  }
  return current;
}

/** @param {string} reference */
export function schemaNameFromReference(reference) {
  const prefix = '#/components/schemas/';
  if (!reference.startsWith(prefix)) return null;
  const tail = decodeURIComponent(reference.slice(prefix.length));
  if (tail.includes('/')) return null;
  return tail.replace(/~1/g, '/').replace(/~0/g, '~');
}

/** @param {Record<string, any> | boolean | undefined} schema @returns {string} */
export function describeSchema(schema) {
  if (schema === false) return 'No value permitted';
  if (schema === true || !schema) return 'Unconstrained';
  if (schema.$ref) return schemaNameFromReference(schema.$ref) ?? schema.$ref;
  if (schema.anyOf) return schema.anyOf.map(describeSchema).join(' | ');
  if (schema.oneOf) return `One of: ${schema.oneOf.map(describeSchema).join(' | ')}`;
  if (schema.allOf) return `All of: ${schema.allOf.map(describeSchema).join(' + ')}`;
  if (schema.type === 'array') return `Array of ${describeSchema(schema.items)}`;
  const type = Array.isArray(schema.type) ? schema.type.join(' | ') : schema.type ?? (schema.properties ? 'object' : 'Unspecified');
  return schema.format ? `${type} (${schema.format})` : type;
}

/** @param {Record<string, any>} document @param {string} expectedVersion */
export function validateOpenApi(document, expectedVersion) {
  if (!document || !/^3\.(0|1)\.\d+$/.test(document.openapi ?? '')) throw new Error('Expected an OpenAPI 3.0 or 3.1 document');
  if (document.info?.version !== expectedVersion) throw new Error(`API version must match Python package ${expectedVersion}`);
  if (typeof document.info?.title !== 'string' || !document.info.title.trim()) throw new Error('API title is required');
  if (!document.paths || typeof document.paths !== 'object' || Array.isArray(document.paths)) throw new Error('OpenAPI paths are required');
  const operations = catalogOperations(document);
  if (!operations.length) throw new Error('OpenAPI must contain operations');
  const ids = new Set();
  for (const operation of operations) {
    if (!operation.path.startsWith('/')) throw new Error(`Invalid API path: ${operation.path}`);
    if (typeof operation.id !== 'string' || !operation.id.trim()) throw new Error(`Missing operationId: ${operation.method} ${operation.path}`);
    if (ids.has(operation.id)) throw new Error(`Duplicate operationId: ${operation.id}`);
    ids.add(operation.id);
  }
  for (const reference of collectReferences(document)) resolveReference(document, reference);
  return {
    paths: Object.keys(document.paths).length,
    operations: operations.length,
    schemas: Object.keys(document.components?.schemas ?? {}).length,
  };
}
