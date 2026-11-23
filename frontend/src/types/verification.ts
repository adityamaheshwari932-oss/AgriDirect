/**
 * Domain types for AgriDirect Verification System.
 * Aligned with backend Pydantic models in app.verification.schemas.
 */

export type FarmerDocumentType =
  | "kisan_credit_card"
  | "land_ownership"
  | "government_id"
  | "organic_certification"
  | "other";

export type BuyerDocumentType =
  | "gstin_certificate"
  | "trade_license"
  | "fssai_license"
  | "incorporation_certificate"
  | "pan_card"
  | "other";

export type TransporterDocumentType =
  | "vehicle_rc"
  | "driving_license"
  | "transport_permit"
  | "business_registration"
  | "insurance_certificate"
  | "fitness_certificate"
  | "pollution_certificate"
  | "government_id"
  | "other";

export type VerificationDocumentType = FarmerDocumentType | BuyerDocumentType | TransporterDocumentType | string;

export type SubmissionStatus = "pending" | "approved" | "rejected";

export interface VerificationDocument {
  id: string;
  submission_id: string;
  document_type: string;
  document_number?: string | null;
  file_mime_type: string;
  file_size_bytes: number;
  created_at: string;
}

export interface VerificationSubmission {
  id: string;
  user_id: string;
  status: SubmissionStatus;
  submission_notes?: string | null;
  reviewed_by_admin_id?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  created_at: string;
  updated_at: string;
  documents: VerificationDocument[];
  user_email?: string | null;
  user_role?: string | null;
}

export interface VerificationSubmissionCreate {
  submission_notes?: string;
  role?: string;
}

export const FARMER_DOCUMENT_TYPES: { value: FarmerDocumentType; label: string; description: string }[] = [
  {
    value: "land_ownership",
    label: "Land Ownership Record / Title",
    description: "Registered land deed, 7/12 extract, Patta, or agricultural lease agreement",
  },
  {
    value: "kisan_credit_card",
    label: "Kisan Credit Card (KCC) / Farmer Passbook",
    description: "Official institutional agricultural credit card or farmer producer identity document",
  },
  {
    value: "government_id",
    label: "Government Photo Identification",
    description: "Aadhaar card, voter identity card, passport, or state-issued driving license",
  },
  {
    value: "organic_certification",
    label: "Organic / GAP Farming Certification",
    description: "Accredited organic certification (NPOP / PGS-India / USDA Organic) or GAP certificate",
  },
  {
    value: "other",
    label: "Other Supporting Evidence",
    description: "Cooperative society membership or relevant agricultural document",
  },
];

export const BUYER_DOCUMENT_TYPES: { value: BuyerDocumentType; label: string; description: string }[] = [
  {
    value: "gstin_certificate",
    label: "GSTIN Registration Certificate",
    description: "Official Goods and Services Tax Identification Number certificate",
  },
  {
    value: "incorporation_certificate",
    label: "Certificate of Incorporation / Registration",
    description: "Company incorporation certificate (CIN), LLP agreement, or partnership deed",
  },
  {
    value: "fssai_license",
    label: "FSSAI Food Business License",
    description: "Food Safety and Standards Authority of India commercial handling registration",
  },
  {
    value: "trade_license",
    label: "Municipal Trade License / Shop & Establishment",
    description: "Current municipal corporation trade license or commercial establishment certificate",
  },
  {
    value: "pan_card",
    label: "Commercial Entity PAN Card",
    description: "Permanent Account Number card registered to business entity or proprietor",
  },
  {
    value: "other",
    label: "Other Corporate Document",
    description: "Authorized procurement officer letter or corporate power of attorney",
  },
];

export const TRANSPORTER_DOCUMENT_TYPES: { value: TransporterDocumentType; label: string; description: string }[] = [
  {
    value: "vehicle_rc",
    label: "Vehicle Registration Certificate (RC)",
    description: "Official vehicle registration certificate issued by the Regional Transport Office (RTO)",
  },
  {
    value: "driving_license",
    label: "Commercial Driving License",
    description: "Valid commercial motor vehicle (HMV/LMV-TR) driving license for registered driver",
  },
  {
    value: "transport_permit",
    label: "Commercial Goods Carriage Permit",
    description: "State or National goods carriage permit authorizing commercial produce transit",
  },
  {
    value: "business_registration",
    label: "Transport Agency Registration / GSTIN",
    description: "Goods and Services Tax certificate or registered logistics enterprise charter",
  },
  {
    value: "insurance_certificate",
    label: "Commercial Vehicle Insurance Policy",
    description: "Active comprehensive or third-party commercial vehicle insurance cover note",
  },
  {
    value: "fitness_certificate",
    label: "Vehicle Fitness Certificate",
    description: "Current vehicle roadworthiness certificate issued by transport authorities",
  },
  {
    value: "pollution_certificate",
    label: "Pollution Under Control (PUC) Certificate",
    description: "Valid emission standards compliance certificate for the registered vehicle",
  },
  {
    value: "government_id",
    label: "Government Photo Identification",
    description: "Aadhaar card, voter identity card, or passport of the registered fleet manager",
  },
  {
    value: "other",
    label: "Other Transport Authorization",
    description: "Cooperative transit agreement, fleet leasing deed, or state authority authorization",
  },
];

export const MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024; // 10 MiB

export const ALLOWED_FILE_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".webp"] as const;

export const ALLOWED_MIME_TYPES = [
  "application/pdf",
  "image/jpeg",
  "image/png",
  "image/webp",
] as const;
