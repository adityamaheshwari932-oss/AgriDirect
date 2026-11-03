import React, { useEffect, useState } from "react";
import { X, ShieldCheck, Phone, Mail, User, AlertCircle, Loader2, CheckCircle2 } from "lucide-react";
import { chatApi } from "../../api/chat";
import type { ContactDetails } from "../../types/chat";

interface ContactShareModalProps {
  isOpen: boolean;
  conversationId: string;
  hasConsent: boolean;
  onClose: () => void;
  onRequestSent: () => void;
}

export const ContactShareModal: React.FC<ContactShareModalProps> = ({
  isOpen,
  conversationId,
  hasConsent,
  onClose,
  onRequestSent,
}) => {
  const [contacts, setContacts] = useState<ContactDetails | null>(null);
  const [notes, setNotes] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && hasConsent) {
      setIsLoading(true);
      setError(null);
      chatApi
        .getContactDetails(conversationId)
        .then((res) => setContacts(res))
        .catch((err: unknown) => {
          const msg = err instanceof Error ? err.message : "Failed to load contact information.";
          setError(msg);
        })
        .finally(() => setIsLoading(false));
    }
  }, [isOpen, hasConsent, conversationId]);

  if (!isOpen) return null;

  const handleRequestSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    try {
      await chatApi.requestContactSharing(conversationId, {
        notes: notes.trim() ? notes.trim() : null,
      });
      setSuccessMsg("Contact sharing request sent. Awaiting counterparty approval.");
      onRequestSent();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit contact sharing request.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-xs flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-contact-share-title"
    >
      <div className="bg-card w-full max-w-md rounded-2xl border border-border shadow-2xl overflow-hidden my-8 animate-in fade-in zoom-in-95 duration-200">
        <div className="px-6 py-4 border-b border-border flex items-center justify-between bg-secondary/40">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-primary" aria-hidden="true" />
            <h2 id="modal-contact-share-title" className="text-base font-bold text-foreground">
              {hasConsent ? "Direct Contact Information" : "Request Contact Sharing"}
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

        <div className="p-6 space-y-4">
          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" aria-hidden="true" />
              <span>{successMsg}</span>
            </div>
          )}

          {hasConsent ? (
            isLoading ? (
              <div className="py-8 flex flex-col items-center justify-center gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-primary" aria-hidden="true" />
                <span className="text-xs text-muted-foreground">Loading disclosed details...</span>
              </div>
            ) : contacts ? (
              <div className="space-y-3">
                <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-800 text-xs">
                  Mutual consent granted. Contact details disclosed for bilateral trade coordination.
                </div>

                <div className="p-4 rounded-xl border border-border bg-secondary/30 space-y-3 text-xs">
                  <div className="flex items-center gap-2.5">
                    <User className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                    <div>
                      <span className="text-[11px] text-muted-foreground block">Name</span>
                      <span className="font-bold text-foreground">{contacts.name} ({contacts.role})</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <Phone className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                    <div>
                      <span className="text-[11px] text-muted-foreground block">Phone</span>
                      <a href={`tel:${contacts.phone_number}`} className="font-bold text-primary hover:underline">
                        {contacts.phone_number || "Not provided"}
                      </a>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5">
                    <Mail className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                    <div>
                      <span className="text-[11px] text-muted-foreground block">Email</span>
                      <a href={`mailto:${contacts.email}`} className="font-bold text-primary hover:underline">
                        {contacts.email || "Not provided"}
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            ) : null
          ) : (
            <form onSubmit={handleRequestSubmit} className="space-y-4">
              <p className="text-xs text-muted-foreground leading-relaxed">
                AgriDirect safeguards participant privacy. Direct telephone and email contact details are disclosed only after both counterparties explicitly grant mutual consent.
              </p>

              <div className="space-y-1.5">
                <label
                  htmlFor="contact-request-notes"
                  className="block text-xs font-bold uppercase tracking-wider text-muted-foreground"
                >
                  Message to Counterparty (Optional)
                </label>
                <textarea
                  id="contact-request-notes"
                  rows={3}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g., Let's speak on phone to coordinate transport logistics and loading dock address..."
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
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 text-xs font-bold shadow-xs transition-colors disabled:opacity-50 flex items-center gap-2"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                      <span>Sending...</span>
                    </>
                  ) : (
                    <span>Request Contact Disclosure</span>
                  )}
                </button>
              </div>
            </form>
          )}

          {hasConsent && (
            <div className="pt-2 flex justify-end">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl border border-border bg-card text-foreground hover:bg-secondary text-xs font-semibold transition-colors"
              >
                Close
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

