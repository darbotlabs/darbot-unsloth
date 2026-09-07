import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const repository = 'https://github.com/darbotlabs/darbot-unsloth';

const config: Config = {
  title: 'Darbot Unsloth',
  tagline: 'A source-first guide to local models, training, and Studio.',
  favicon: 'img/mark.svg',
  url: 'https://darbotlabs.github.io',
  baseUrl: '/darbot-unsloth/',
  organizationName: 'darbotlabs',
  projectName: 'darbot-unsloth',
  trailingSlash: true,
  onBrokenLinks: 'throw',
  onBrokenAnchors: 'throw',
  markdown: {
    hooks: {
      onBrokenMarkdownLinks: 'throw',
      onBrokenMarkdownImages: 'throw',
    },
  },
  i18n: {defaultLocale: 'en', locales: ['en']},
  presets: [
    [
      'classic',
      {
        docs: {
          sidebarPath: './sidebars.ts',
          editUrl: `${repository}/edit/main/website/`,
          breadcrumbs: true,
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {customCss: './src/css/custom.css'},
        sitemap: {changefreq: 'weekly', priority: 0.5},
      } satisfies Preset.Options,
    ],
  ],
  themes: [
    [
      '@easyops-cn/docusaurus-search-local',
      {
        hashed: true,
        language: ['en'],
        indexDocs: true,
        indexBlog: false,
        indexPages: true,
        highlightSearchTermsOnTargetPage: true,
        searchResultLimits: 10,
      },
    ],
  ],
  themeConfig: {
    image: 'img/social-card.svg',
    metadata: [
      {name: 'description', content: 'The Darbot Unsloth wiki: source installation, CPython 3.14, backend profiles, LoRA and QLoRA, Studio, APIs, updates, and verified release downloads.'},
      {name: 'theme-color', content: '#133f35'},
    ],
    colorMode: {respectPrefersColorScheme: true},
    navbar: {
      title: 'Darbot Unsloth',
      logo: {alt: 'Darbot Unsloth home', src: 'img/mark.svg', width: 32, height: 32},
      items: [
        {type: 'docSidebar', sidebarId: 'wiki', position: 'left', label: 'Wiki'},
        {to: '/downloads', label: 'Downloads', position: 'left'},
        {to: '/docs/support', label: 'Support & scope', position: 'left'},
        {href: repository, label: 'GitHub', position: 'right'},
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {title: 'Start here', items: [
          {label: 'Choose an installation', to: '/docs/getting-started'},
          {label: 'Dependency matrix', to: '/docs/dependency-matrix'},
          {label: 'Downloads & release status', to: '/downloads'},
        ]},
        {title: 'Build & operate', items: [
          {label: 'Architecture', to: '/docs/architecture'},
          {label: 'Updates & recovery', to: '/docs/updates'},
          {label: 'Security & privacy', to: '/docs/security'},
        ]},
        {title: 'Project', items: [
          {label: 'Fork source', href: repository},
          {label: 'Upstream Unsloth', href: 'https://github.com/unslothai/unsloth'},
          {label: 'Attribution & licenses', to: '/docs/licenses'},
        ]},
      ],
      copyright: 'Darbot Labs maintains this independent fork of Unsloth, originally developed by Unsloth AI. Original licenses and attribution apply. Built with Docusaurus.',
    },
    tableOfContents: {minHeadingLevel: 2, maxHeadingLevel: 3},
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['powershell', 'bash', 'python', 'toml', 'json', 'yaml'],
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
