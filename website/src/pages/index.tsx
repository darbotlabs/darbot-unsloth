import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import release from '@site/src/data/release.json';
import styles from './index.module.css';

const guides = [
  {number: '01', title: 'Install with intent', to: '/docs/getting-started', text: 'Choose Windows, Linux, or macOS. Keep the Python environment separate from your data and select the right backend.'},
  {number: '02', title: 'Train a first adapter', to: '/docs/training', text: 'Understand LoRA, genuine packed 4-bit QLoRA, dataset preparation, and the limits of hardware qualification.'},
  {number: '03', title: 'Make Studio your own', to: '/docs/studio', text: 'Work with local chat, data recipes, audio, and an authenticated API without confusing the UI with the runtime.'},
  {number: '04', title: 'Know what is installed', to: '/docs/dependency-matrix', text: 'Read the exact interpreter, Torch, Triton, framework, and native-artifact policy—plus the reasons for compatibility exceptions.'},
  {number: '05', title: 'Understand the system', to: '/docs/architecture', text: 'Follow the boundaries between Core, the maintained Zoo companion, FastAPI, workers, React, and the Tauri desktop shell.'},
  {number: '06', title: 'Update without guessing', to: '/docs/updates', text: 'Distinguish tracked source updates from immutable repair snapshots. Preserve local work, provenance, and recovery material.'},
];

export default function Home(): ReactNode {
  return (
    <Layout title="Local models. Documented boundaries." description="A practical, source-first wiki for Darbot Unsloth: installation, local chat, LoRA and QLoRA training, APIs, maintenance, and release downloads.">
      <header className={styles.hero}>
        <div className="container">
          <div className={styles.eyebrow}>THE DARBOT UNSLOTH WIKI</div>
          <h1>Local models.<br /><span>Documented boundaries.</span></h1>
          <p className={styles.lead}>From a clean environment to a saved adapter. A practical guide to running, training, and maintaining this independent Unsloth fork.</p>
          <div className={styles.actions}>
            <Link className="button button--primary button--lg" to="/docs/getting-started">Start with the right setup</Link>
            <Link className="button button--secondary button--lg" to="/docs/overview">Explore the wiki</Link>
          </div>
          <div className={styles.facts} aria-label="Current compatibility policy">
            <span><strong>3.14.7+</strong> standard CPython, below 3.15</span>
            <span><strong>2.14 / cu130</strong> canonical NVIDIA stack</span>
            <span><strong>GGUF-only</strong> a genuinely Torch-free profile</span>
          </div>
        </div>
      </header>
      <main>
        <section className={`container ${styles.release}`}>
          <div>
            <span className="status-badge">{release.status === 'published' ? 'Release published' : 'Release preparation'}</span>
            <h2>Desktop {release.desktopVersion} · Python {release.pythonVersion}</h2>
            <p>Separate version schemes, one documented source. Check publication status and qualification notes before downloading.</p>
          </div>
          <Link className="button button--outline button--primary" to="/downloads">View release status →</Link>
        </section>
        <section className={`container ${styles.section}`} aria-labelledby="paths">
          <div className={styles.sectionHeading}>
            <div><div className={styles.eyebrow}>YOUR NEXT STEP</div><h2 id="paths">A field guide, not a feature promise.</h2></div>
            <p>Start with a task. Follow its constraints through the system.</p>
          </div>
          <div className={styles.grid}>
            {guides.map((guide) => (
              <Link key={guide.number} className={styles.card} to={guide.to}>
                <span className={styles.number}>{guide.number}</span>
                <h3>{guide.title} <span aria-hidden="true">↗</span></h3>
                <p>{guide.text}</p>
              </Link>
            ))}
          </div>
        </section>
        <section className={`container ${styles.scope}`}>
          <div><div className={styles.eyebrow}>EVIDENCE BEFORE CLAIMS</div><h2>Know the difference between configured and qualified.</h2></div>
          <div>
            <p>Offline tiny-Llama LoRA and 4-bit QLoRA were exercised separately on two physical T1000 8 GB GPUs. That is not pooled 16 GB VRAM, distributed-training certification, or a guarantee for every model.</p>
            <Link to="/docs/support">Read the qualification and support scope →</Link>
          </div>
        </section>
        <section className={`container ${styles.attribution}`}>
          <h2>Built on Unsloth. Clearly a fork.</h2>
          <p>Unsloth Core and Studio originate with the Unsloth AI team. This wiki documents the Darbot-maintained stack and its narrower qualification scope; upstream downloads and notebooks are not fork release artifacts.</p>
          <Link to="/docs/licenses">Read attribution and licensing</Link>
        </section>
      </main>
    </Layout>
  );
}
