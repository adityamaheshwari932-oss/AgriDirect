import React, { useState } from "react";
import { X, Upload, AlertCircle, FileText, Image } from "lucide-react";

interface AttachmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAttach: (file: File, caption: string) => void;
}

const ALLOWED_EXTENSIONS = [
  ".jpg",
  ".jpeg",
  ".png",
  ".webp",
  ".pdf",
  ".doc",
  ".docx",
  ".xls",
  ".xlsx",
  ".csv",
  ".txt",
];

const MAX_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

export const AttachmentModal: React.FC<AttachmentModalProps> = ({
  isOpen,
  onClose,
  onAttach,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [caption, setCaption] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];

      if (file.size > MAX_SIZE_BYTES) {
        setError("File size exceeds 10 MB limit.");
        return;
      }

      const ext = "." + (file.name.split(".").pop()?.toLowerCase() || "");
      if (!ALLOWED_EXTENSIONS.includes(ext)) {
        setError(
          `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`
        );
        return;
      }

      setSelectedFile(file);
    }
  };

  const handleConfirm = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a file to attach.");
      return;
    }

    onAttach(selectedFile, caption.trim());
    setSelectedFile(null);
    setCaption("");
    onClose();
  };

  const isImage = selectedFile?.type.startsWith("image/");

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-attachment-title"
    >
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2">
            <Upload className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 id="modal-attachment-title" className="text-base font-bold text-foreground">
              Attach File to Message
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary focus:outline-none focus:ring-2 focus:ring-primary"
            aria-label="Close dialog"
          >
            <X className="w-5 h-5" aria-hidden="true" />
          </button>
        </div>

        <form onSubmit={handleConfirm} className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="block text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Select Image or Document (Max 10MB)
            </label>
            <input
              type="file"
              accept=".jpg,.jpeg,.png,.webp,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
              onChange={handleFileChange}
              className="text-xs text-muted-foreground file:mr-3 file:py-2 file:px-3.5 file:rounded-xl file:border file:border-border file:text-xs file:font-bold file:bg-secondary file:text-foreground hover:file:bg-secondary/80 cursor-pointer w-full"
            />
          </div>

          {selectedFile && (
            <div className="p-3 rounded-xl bg-secondary/50 border border-border flex items-center gap-3 text-xs">
              {isImage ? (
                <Image className="w-5 h-5 text-primary shrink-0" aria-hidden="true" />
              ) : (
                <FileText className="w-5 h-5 text-primary shrink-0" aria-hidden="true" />
              )}
              <div className="truncate">
                <p className="font-bold text-foreground truncate">{selectedFile.name}</p>
                <p className="text-[11px] text-muted-foreground">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label
              htmlFor="attachment-caption-input"
              className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
            >
              Accompanying Message Caption
            </label>
            <input
              id="attachment-caption-input"
              type="text"
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              placeholder="Add an optional comment..."
              maxLength={500}
              className="w-full rounded-xl border border-border bg-card px-3.5 py-2 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-primary font-medium"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-3 border-t border-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!selectedFile}
              className="px-5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50"
            >
              Send Attachment
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

