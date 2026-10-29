import React, { useState } from "react";
import { Download, FileText, Loader2, AlertCircle, Calendar, Hash } from "lucide-react";
import { verificationApi } from "../../api/verification";
import { ApiError } from "../../api/errors";
import type { VerificationDocument } from "../../types/verification";
import { formatFileSize, getDocumentTypeLabel } from "../../utils/status";

interface VerificationDocumentsListProps {
  documents: VerificationDocument[];
}

export const VerificationDocumentsList: React.FC<VerificationDocumentsListProps> = ({ documents }) => {
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const handleDownload = async (doc: VerificationDocument) => {
    setDownloadingId(doc.id);
    setDownloadError(null);

    try {
      const { blob, filename } = await verificationApi.downloadVerificationDocument(doc.id);

      // Determine appropriate filename
      const fallbackExt = doc.file_mime_type.includes("pdf")
        ? ".pdf"
        : doc.file_mime_type.includes("png")
        ? ".png"
        : doc.file_mime_type.includes("webp")
        ? ".webp"
        : ".jpg";
      const downloadName = filename || `${doc.document_type}-${doc.id.slice(0, 8)}${fallbackExt}`;

      const blobUrl = window.URL.createObjectURL(blob);
      const tempLink = document.createElement("a");
      tempLink.href = blobUrl;
      tempLink.download = downloadName;
      document.body.appendChild(tempLink);
      tempLink.click();
      document.body.removeChild(tempLink);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setDownloadError(err.message || "Failed to download document. Please retry.");
      } else {
        setDownloadError("A network error occurred while downloading the document.");
      }
    } finally {
      setDownloadingId(null);
    }
  };

  if (!documents || documents.length === 0) {
    return (
      <div className="p-8 text-center border rounded-xl bg-card border-border text-muted-foreground space-y-2">
        <FileText className="w-8 h-8 mx-auto text-muted-foreground/60" aria-hidden="true" />
        <p className="text-sm font-medium text-foreground">No verification evidence documents attached yet.</p>
        <p className="text-xs">
          Select your required document category above and upload a valid PDF or image file.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3" aria-label="Attached Verification Documents">
      {downloadError && (
        <div
          className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-900 text-xs flex items-center gap-2"
          role="alert"
        >
          <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" aria-hidden="true" />
          <span>{downloadError}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {documents.map((doc) => {
          const isDownloading = downloadingId === doc.id;
          const formattedDate = new Date(doc.created_at).toLocaleDateString(undefined, {
            year: "numeric",
            month: "short",
            day: "numeric",
          });

          return (
            <div
              key={doc.id}
              className="p-4 rounded-xl border border-border bg-card shadow-xs flex flex-col justify-between gap-3 hover:border-primary/40 transition-colors"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                      <FileText className="w-4 h-4" aria-hidden="true" />
                    </div>
                    <div>
                      <span className="text-xs font-bold text-foreground block leading-tight">
                        {getDocumentTypeLabel(doc.document_type)}
                      </span>
                      <span className="text-[11px] text-muted-foreground font-mono">
                        {doc.file_mime_type} • {formatFileSize(doc.file_size_bytes)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="space-y-1 text-xs text-muted-foreground pt-1 border-t border-border/60">
                  {doc.document_number && (
                    <div className="flex items-center gap-1.5">
                      <Hash className="w-3.5 h-3.5 text-muted-foreground/70" aria-hidden="true" />
                      <span className="font-mono text-foreground">{doc.document_number}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5 text-muted-foreground/70" aria-hidden="true" />
                    <span>Uploaded on {formattedDate}</span>
                  </div>
                </div>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => handleDownload(doc)}
                  disabled={isDownloading}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-secondary/50 text-foreground hover:bg-secondary text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50"
                  aria-label={`Download ${getDocumentTypeLabel(doc.document_type)}`}
                >
                  {isDownloading ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" aria-hidden="true" />
                      <span>Downloading...</span>
                    </>
                  ) : (
                    <>
                      <Download className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>Download</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
