import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  wiki: [
    'overview',
    {type: 'category', label: 'Install & choose a profile', collapsed: false, items: [
      'getting-started', 'windows', 'linux-macos', 'gguf-only', 'dependency-matrix', 'devices',
    ]},
    {type: 'category', label: 'Use Studio & train', items: [
      'studio', 'training', 'datasets', 'data-recipes', 'audio', 'api',
      {type: 'link', label: 'API reference & models', href: '/api-reference'},
      'mcp', 'export',
    ]},
    {type: 'category', label: 'Understand & operate', items: [
      'architecture', 'storage', 'updates', 'builds-releases', 'security',
    ]},
    {type: 'category', label: 'Develop & get help', items: [
      'testing', 'support', 'troubleshooting', 'contributing', 'licenses',
    ]},
  ],
};

export default sidebars;
