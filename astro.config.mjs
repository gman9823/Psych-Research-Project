// @ts-check
import { defineConfig } from 'astro/config';
import node from '@astrojs/node';

import tunnel from 'astro-tunnel';

// https://astro.build/config
export default defineConfig({
  // The survey and contact APIs require runtime server execution with Node.
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  integrations: [tunnel({
    acceptCloudflareNotice: true
  })]
});