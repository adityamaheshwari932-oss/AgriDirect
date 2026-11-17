import React, { useState, useRef } from "react";
import { Upload, FileText, CheckCircle2, AlertCircle, X, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { verificationApi } from "../../api/verification";
import { ApiError } from "../../api/errors";
import {
  ALLOWED_FILE_EXTENSIONS,
  ALLOWED_MIME_TYPES,
  BUYER_DOCUMENT_TYPES,
  FARMER_DOCUMENT_TYPES,
  MAX_DOCUMENT_SIZE_BYTES,
  type VerificationDocument,
} from "../../types/verification";
import { formatFileSize } from "../../utils/status";

interface VerificationDocumentUploadFormProps {
  role: "farmer" | "buyer";
  onUploadSuccess: (document: VerificationDocument) => void;
  disabled?: boolean;
}

export const VerificationDocumentUploadForm: React.FC<VerificationDocumentUploadFormProps> = ({
  role,
  onUploadSuccess,
  disabled = false,
}) => {
  const { t } = useTranslation(["verification", "common", "errors"]);
  const documentTypeOptions = role === "farmer" ? FARMER_DOCUMENT_TYPES : BUYER_DOCUMENT_TYPES;

  const [selectedType, setSelectedType] = useState<string>(documentTypeOptions[0].value);
  const [documentNumber, setDocumentNumber] = useState<string>("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadSuccessMessage, setUploadSuccessMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValidationError(null);
    setApiError(null);
    setUploadSuccessMessage(null);

    const files = e.target.files;
    if (!files || files.length === 0) {
      setSelectedFile(null);
      return;
    }

    const file = files[0];

    // Frontend validation: file size
    if (file.size > MAX_DOCUMENT_SIZE_BYTES) {
      setValidationError(
        t(
          "verification:file_size_exceeded",
          `File size (${formatFileSize(file.size)}) exceeds the maximum permitted limit of 10 MiB.`,
          { size: formatFileSize(file.size) }
        )
      );
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    // Frontend validation: file extension & mime type
    const lowerName = file.name.toLowerCase();
    const hasValidExt = ALLOWED_FILE_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
    const hasValidMime =
      !file.type || (ALLOWED_MIME_TYPES as readonly string[]).includes(file.type);

    if (!hasValidExt || !hasValidMime) {
      setValidationError(
        t(
          "verification:unsupported_file_format",
          "Unsupported file format. Please select a PDF, JPEG, PNG, or WebP document."
        )
      );
      setSelectedFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      return;
    }

    setSelectedFile(file);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setValidationError(null);
    setApiError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);
    setApiError(null);
    setUploadSuccessMessage(null);

    if (!selectedFile) {
      setValidationError(t("verification:select_file_validation", "Please select a document file to upload."));
      return;
    }

    setIsUploading(true);

    try {
      const doc = await verificationApi.uploadVerificationDocument(
        selectedFile,
        selectedType,
        documentNumber
      );

      setUploadSuccessMessage(
        t(
          "verification:upload_success_attached",
          `Document "${selectedFile.name}" was uploaded successfully and attached to your application.`,
          { filename: selectedFile.name }
        )
      );
      setSelectedFile(null);
      setDocumentNumber("");
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }

      onUploadSuccess(doc);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setApiError(err.message || t("verification:upload_failed_error", "Failed to upload document. Please verify the file and try again."));
      } else {
        setApiError(t("common:network_error_retry", "A network error occurred while uploading. Please check your connection and retry."));
      }
    } finally {
      setIsUploading(false);
    }
  };

  const selectedTypeObj = documentTypeOptions.find((d) => d.value === selectedType);

  return (
    <form onSubmit={handleSubmit} className="space-y-5" aria-label="Evidence Document Upload Form">
      {/* Upload Success Alert */}
      {uploadSuccessMessage && (
        <div
          className="p-3.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-900 text-sm flex items-start gap-2.5"
          role="status"
        >
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <span className="flex-1 font-medium">{uploadSuccessMessage}</span>
          <button
            type="button"
            onClick={() => setUploadSuccessMessage(null)}
            className="text-emerald-700 hover:text-emerald-900"
            aria-label={t("common:dismiss", "Dismiss success message")}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* API / Validation Error Alert */}
      {(validationError || apiError) && (
        <div
          className="p-3.5 rounded-lg bg-red-50 border border-red-200 text-red-900 text-sm flex items-start gap-2.5"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="flex-1 space-y-1">
            <p className="font-semibold">
              {validationError
                ? t("verification:invalid_file_selection", "Invalid File Selection")
                : t("verification:upload_failed", "Upload Failed")}
            </p>
            <p className="text-xs text-red-800">{validationError || apiError}</p>
          </div>
          <button
            type="button"
            onClick={() => {
              setValidationError(null);
              setApiError(null);
            }}
            className="text-red-700 hover:text-red-900"
            aria-label={t("common:dismiss_error", "Dismiss error")}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Document Category Select */}
        <div className="space-y-1.5">
          <label htmlFor="document-type-select" className="block text-xs font-semibold text-foreground">
            {t("verification:document_category_label", "Document Category")} <span className="text-red-500">*</span>
          </label>
          <select
            id="document-type-select"
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            disabled={disabled || isUploading}
            className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {documentTypeOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {selectedTypeObj && (
            <p className="text-xs text-muted-foreground">{selectedTypeObj.description}</p>
          )}
        </div>

        {/* Document / Registration Number Input */}
        <div className="space-y-1.5">
          <label htmlFor="document-number-input" className="block text-xs font-semibold text-foreground">
            {t("verification:document_number_label", "Document / Certificate Number")}{" "}
            <span className="text-xs text-muted-foreground font-normal">({t("common:optional", "Optional")})</span>
          </label>
          <input
            id="document-number-input"
            type="text"
            value={documentNumber}
            onChange={(e) => setDocumentNumber(e.target.value)}
            placeholder={
              role === "farmer"
                ? t("verification:number_placeholder_farmer", "e.g. KCC-987654 or Land Deed # 124")
                : t("verification:number_placeholder_buyer", "e.g. 27AAAAA0000A1Z5 or FSSAI # 1001")
            }
            maxLength={64}
            disabled={disabled || isUploading}
            className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60 disabled:cursor-not-allowed"
          />
          <p className="text-xs text-muted-foreground">{t("verification:number_hint", "Identifying registration number if visible on the document")}</p>
        </div>
      </div>

      {/* File Drop / Select Area */}
      <div className="space-y-1.5">
        <label className="block text-xs font-semibold text-foreground">
          {t("verification:document_file_label", "Document File")} <span className="text-red-500">*</span>
        </label>

        {!selectedFile ? (
          <div
            onClick={() => !disabled && !isUploading && fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-colors ${disabled || isUploading
              ? "opacity-60 cursor-not-allowed border-border bg-muted/20"
              : "border-border hover:border-primary/60 hover:bg-primary/5 bg-card"
              }`}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                fileInputRef.current?.click();
              }
            }}
            aria-label={t("verification:select_file_cta_aria", "Click or press enter to select verification document file")}
          >
            <div className="w-10 h-10 rounded-full bg-secondary mx-auto flex items-center justify-center text-primary mb-2">
              <Upload className="w-5 h-5" aria-hidden="true" />
            </div>
            <div className="text-sm font-medium text-foreground">
              {t("verification:click_choose_file", "Click to choose a verification document file")}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {t("verification:accepted_formats", "Accepted formats: PDF, JPEG, PNG, or WebP (Maximum size: 10 MiB)")}
            </p>
          </div>
        ) : (
          <div className="p-4 rounded-xl border border-border bg-secondary/30 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center flex-shrink-0">
                <FileText className="w-5 h-5" aria-hidden="true" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground truncate">{selectedFile.name}</p>
                <p className="text-xs text-muted-foreground">
                  {t("common:size", "Size")}: {formatFileSize(selectedFile.size)} • {t("common:type", "Type")}: {selectedFile.type || t("verification:document_file", "Document file")}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={handleRemoveFile}
              disabled={isUploading}
              className="p-1.5 rounded-md text-muted-foreground hover:text-red-600 hover:bg-red-50 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500"
              aria-label={t("verification:remove_selected_file", "Remove selected file")}
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,.webp,application/pdf,image/jpeg,image/png,image/webp"
          onChange={handleFileChange}
          className="hidden"
          disabled={disabled || isUploading}
          aria-hidden="true"
        />
      </div>

      {/* Submit Button */}
      <div className="flex items-center justify-end gap-3 pt-2">
        <button
          type="submit"
          disabled={!selectedFile || isUploading || disabled}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-primary text-primary-foreground font-semibold text-sm hover:bg-primary-800 transition-colors focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 disabled:cursor-not-allowed shadow-xs"
        >
          {isUploading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
              <span>{t("verification:uploading_evidence", "Uploading Evidence...")}</span>
            </>
          ) : (
            <>
              <Upload className="w-4 h-4" aria-hidden="true" />
              <span>{t("verification:upload_document", "Upload Document")}</span>
            </>
          )}
        </button>
      </div>
    </form>
  );
};
