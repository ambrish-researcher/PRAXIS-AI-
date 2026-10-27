// Vercel server-side same-origin proxy. No inference or backend secrets enter the bundle.
import { Readable } from "node:stream";
import { pipeline } from "node:stream/promises";
export default async function handler(req, res) {
  const configured = process.env.PRAXIS_BACKEND_URL;
  if (!configured) {
    res.statusCode = 503;
    return res.end("PRAXIS_BACKEND_URL is not configured");
  }
  let target;
  try {
    const base = new URL(configured);
    if (
      base.protocol !== "https:" ||
      base.username ||
      base.password ||
      base.search ||
      base.hash
    )
      throw Error("Invalid backend URL");
    target = new URL(req.url, base.origin);
    if (target.origin !== base.origin || !target.pathname.startsWith("/api/"))
      throw Error("Invalid API path");
  } catch {
    res.statusCode = 503;
    return res.end("Invalid backend proxy configuration");
  }
  const headers = {};
  for (const name of [
    "content-type",
    "accept",
    "cookie",
    "origin",
    "last-event-id",
  ])
    if (req.headers[name]) headers[name] = req.headers[name];
  const method = req.method || "GET";
  let body;
  if (!["GET", "HEAD"].includes(method)) {
    body =
      typeof req.body === "object" && req.body !== null
        ? JSON.stringify(req.body)
        : req.body;
    if (body && Buffer.byteLength(body) > 1500000) {
      res.statusCode = 413;
      return res.end("Request too large");
    }
  }
  try {
    const upstream = await fetch(target, {
      method,
      headers,
      body,
      redirect: "manual",
      signal: AbortSignal.timeout(55000),
    });
    res.statusCode = upstream.status;
    for (const name of [
      "content-type",
      "content-disposition",
      "cache-control",
      "x-content-type-options",
    ]) {
      const value = upstream.headers.get(name);
      if (value) res.setHeader(name, value);
    }
    const cookies = upstream.headers.getSetCookie();
    if (cookies.length) res.setHeader("set-cookie", cookies);
    if (upstream.body) await pipeline(Readable.fromWeb(upstream.body), res);
    else res.end();
  } catch {
    if (!res.headersSent) {
      res.statusCode = 502;
      res.end(
        "PRAXIS backend is unavailable or the stream expired. The client reconnects to durable events.",
      );
    } else res.end();
  }
}
