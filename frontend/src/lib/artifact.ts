import type { AxiosResponse } from "axios";
import { toast } from "sonner";
import { api } from "./api";

/** Pick a sensible filename extension from the response content-type. */
function extensionFor(contentType: string): string {
  const map: Record<string, string> = {
    "application/pdf": "pdf",
    "image/svg+xml": "svg",
    "image/png": "png",
    "text/html": "html",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
  };
  return map[contentType.split(";")[0].trim()] ?? "bin";
}

/** Content types that are safe (and useful) to render inline in a browser tab. */
const INLINE_VIEWABLE = new Set([
  "application/pdf",
  "image/svg+xml",
  "image/png",
  "text/html",
]);

/**
 * Fetch an artifact with the user's JWT and open it.
 *
 * - HTML / PDF / SVG / PNG → open in a new tab (browser renders inline).
 * - DOCX / PPTX → trigger a download (browsers can't render those inline).
 *
 * Popup-blocker safety: `window.open` is only treated as user-initiated if
 * called *synchronously* inside the click handler. Because the artifact
 * fetch is async, we open a blank placeholder tab first and navigate it to
 * the blob URL once the fetch completes.
 *
 * We deliberately DON'T pass `noopener,noreferrer` here — those features
 * make `window.open` return `null` per spec ("If the noopener feature is
 * set, the returned reference is null"), which would defeat the whole
 * point of getting a Window handle to navigate. Once the navigation
 * completes we set `tab.opener = null` ourselves to sever the back-ref.
 */
export async function openArtifact(
  contentId: number,
  opts?: { title?: string },
): Promise<void> {
  // Open synchronously inside the click handler so the browser treats it as
  // user-initiated. Note: no `noopener` — we need the Window reference.
  const tab = window.open("about:blank", "_blank");

  let response: AxiosResponse<Blob>;
  try {
    response = await api.get<Blob>(`/generated-content/${contentId}/artifact`, {
      responseType: "blob",
    });
  } catch (err) {
    // Don't leave a blank tab hanging if the fetch fails.
    tab?.close();
    // For 4xx errors the backend returns JSON in the response body
    // (e.g. {"detail": "Auto-heal failed: ..."}). Axios delivers it
    // as a Blob because we asked for responseType:"blob" — convert
    // back to text so the user sees an actionable error message in
    // the toast instead of the generic axios "Request failed with
    // status code 410". Falls through to the original error if the
    // response shape isn't recognisable.
    const axiosErr = err as { response?: { status?: number; data?: Blob } };
    const blobBody = axiosErr?.response?.data;
    if (blobBody instanceof Blob) {
      try {
        const text = await blobBody.text();
        const parsed = JSON.parse(text) as { detail?: string };
        const status = axiosErr.response?.status ?? "?";
        if (parsed?.detail) {
          toast.error(`Couldn't open simulation (HTTP ${status}): ${parsed.detail}`);
          return;
        }
      } catch {
        /* fall through */
      }
    }
    // Network errors (no response from server) also land here. Distinguish
    // these from server errors so admins can tell whether the request
    // even arrived.
    if (!axiosErr?.response) {
      toast.error(
        "Network error reaching the server. Check your connection; if it persists, the backend may be down or returning a 5xx without CORS headers.",
      );
      return;
    }
    throw err;
  }

  const contentType = String(
    response.headers["content-type"] ?? "application/octet-stream",
  );
  const inlineKey = contentType.split(";")[0].trim();
  const ext = extensionFor(contentType);
  const blob = new Blob([response.data], { type: contentType });
  const objectUrl = URL.createObjectURL(blob);

  if (INLINE_VIEWABLE.has(inlineKey)) {
    if (tab && !tab.closed) {
      // Navigate the placeholder tab to the rendered artifact. The browser
      // sees a real Content-Type on the blob and renders it inline.
      tab.location.href = objectUrl;
      // Sever the back-reference: the new tab can't poke at this window via
      // `window.opener`. Wrapped in try/catch because cross-origin rules
      // sometimes block the assignment (blob URL origin semantics are odd).
      try {
        tab.opener = null;
      } catch {
        /* ignore */
      }
    } else {
      // Synchronous popup somehow still blocked (some adblockers / strict
      // browser settings). Surface a clear error rather than silently
      // downloading the simulation.
      URL.revokeObjectURL(objectUrl);
      toast.error(
        "Couldn't open the simulation in a new tab. Allow pop-ups for this site and try again.",
      );
      return;
    }
  } else {
    // Not browser-renderable (DOCX / PPTX). Close the placeholder tab and
    // download the file — there's no in-browser viewer for these formats.
    tab?.close();
    triggerDownload(objectUrl, filenameFor(contentId, opts?.title, ext));
  }

  // Keep the blob alive long enough for the new tab to load it. 60s is
  // plenty even on a slow connection.
  setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
}

function triggerDownload(url: string, filename: string): void {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function filenameFor(
  contentId: number,
  title: string | undefined,
  ext: string,
): string {
  const stem =
    (title ?? `content-${contentId}`)
      .replace(/[^a-zA-Z0-9-_. ]+/g, "")
      .trim() || `content-${contentId}`;
  return `${stem}.${ext}`;
}
