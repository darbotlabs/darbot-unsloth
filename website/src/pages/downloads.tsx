import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import release from '@site/src/data/release.json';

const releasesUrl = 'https://github.com/darbotlabs/darbot-unsloth/releases';
const published = release.status === 'published';

export default function Downloads(): ReactNode {
  return (
    <Layout title="Downloads & release status" description="Publication status for Darbot Unsloth desktop and Python packages. Read qualification notes, unsigned-build notices, and checksum guidance before downloading.">
      <main className="container release-page">
        <span className="status-badge">{published ? 'Published' : 'Preparing · not yet available here'}</span>
        <h1>Downloads & release status</h1>
        <p className="intro">Desktop {release.desktopVersion} and Python {release.pythonVersion} use different version schemes. GitHub Releases hosts the binaries; this site documents what they contain and when they are ready.</p>
        <div className="release-notice">
          <h2>{published ? `Release ${release.tag}` : `${release.tag} is in preparation`}</h2>
          <p>{release.summary}</p>
          {published && release.publishedAt && <p>Published: <time dateTime={release.publishedAt}>{release.publishedAt}</time></p>}
          {!published && <p>Production installation checks and bug-bash work are still in progress. The filenames below are the intended assets, not download links or a statement of availability.</p>}
          <p><strong>{release.desktopSigned ? 'Check the release notes for signing details.' : 'Windows desktop builds are unsigned.'}</strong> Automatic signed desktop updates remain disabled. There are no published signing-key claims in this wiki.</p>
        </div>
        <div className="release-links">
          <Link className="button button--primary" href={published ? `${releasesUrl}/tag/${release.tag}` : releasesUrl}>Open GitHub Releases</Link>
          <Link className="button button--secondary" to="/docs/getting-started">Install from source</Link>
        </div>
        <h2>{published ? 'Release assets' : 'Planned release assets'}</h2>
        <table className="release-table">
          <thead><tr><th scope="col">Artifact</th><th scope="col">Filename</th><th scope="col">Purpose</th></tr></thead>
          <tbody>{release.assets.map((asset) => (
            <tr key={asset.name}>
              <th scope="row">{asset.label}</th>
              <td>{published ? <a href={`${releasesUrl}/download/${encodeURIComponent(release.tag)}/${encodeURIComponent(asset.name)}`}>{asset.name}</a> : <code>{asset.name}</code>}</td>
              <td>{asset.description}</td>
            </tr>
          ))}</tbody>
        </table>
        <h2>Before you install</h2>
        <ol>
          <li>Confirm that you are on <code>darbotlabs/darbot-unsloth</code>, not the upstream release page. Read the tag-specific qualification and known-issue notes.</li>
          <li>Match your platform and profile against the <Link to="/docs/dependency-matrix">dependency matrix</Link>. A wheel does not bundle Torch, native helpers, models, or a complete managed environment.</li>
          <li>Download the checksums alongside the artifacts. On Windows, use <code>Get-FileHash -Algorithm SHA256 .\Unsloth_0.2.0_x64-setup.exe</code> and compare the full hash with the corresponding line in <code>SHA256SUMS.txt</code>.</li>
          <li>Back up your data and retain your prior environment before changing installations. Do not disable security controls to run an untrusted unsigned binary.</li>
        </ol>
        <p>Checksums detect mismatches; they do not replace publisher authentication or a signature. Verify the repository, tag, and release provenance as well.</p>
        <h2>Platform and publication boundaries</h2>
        <p>No macOS, Linux, or Docker fork download is promised by this page. Configured build lanes are not published assets or runtime certification. Upstream desktop installers, images, and notebooks do not contain this fork’s changes.</p>
        <p><Link to="/docs/builds-releases">Build and publication process</Link> · <Link to="/docs/support">Qualification scope</Link> · <Link to="/docs/updates">Updates and rollback</Link></p>
      </main>
    </Layout>
  );
}
