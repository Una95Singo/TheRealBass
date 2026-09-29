/**
 * Low Book edge worker.
 *
 * Static assets (the Vite build) are served by the Workers assets binding;
 * only /api/* reaches this code. Phase 3 adds the source-lookup routes here.
 */
export default {
  async fetch(request): Promise<Response> {
    const url = new URL(request.url);

    if (url.pathname === '/api/health') {
      return Response.json({ ok: true, service: 'lowbook', time: new Date().toISOString() });
    }

    return Response.json({ error: 'not found' }, { status: 404 });
  },
} satisfies ExportedHandler;
