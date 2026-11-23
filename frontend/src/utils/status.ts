/**
 * Status and role presentation helpers, labels, style mappings,
 * and profile completion percentage calculators.
 */

import type { AccountStatus, User, VerificationStatus } from "../types";

export interface VerificationPresentation {
  label: string;
  description: string;
  badgeClass: string;
  dotClass: string;
  translationKey: string;
  descriptionKey: string;
}

export const VERIFICATION_STATUS_CONFIG: Record<
  VerificationStatus,
  VerificationPresentation
> = {
  unverified: {
    label: "Not Verified",
    description:
      "Identity and operating credentials not yet submitted. Verification is required before publishing produce listings or entering trade negotiations.",
    badgeClass: "bg-amber-50 text-amber-800 border-amber-300",
    dotClass: "bg-amber-500",
    translationKey: "common:status.unverified",
    descriptionKey: "verification:status_unverified_desc",
  },
  pending: {
    label: "Pending Review",
    description:
      "Verification documents are under administrative review. Direct marketplace trade communications will be unlocked once approved.",
    badgeClass: "bg-blue-50 text-blue-800 border-blue-300",
    dotClass: "bg-blue-500",
    translationKey: "common:status.pending_review",
    descriptionKey: "verification:status_pending_desc",
  },
  verified: {
    label: "Verified",
    description:
      "Account credentials have been verified by AgriDirect administrators. Full access to marketplace listings, negotiations, and trade agreements is active.",
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-300",
    dotClass: "bg-emerald-500",
    translationKey: "common:status.verified",
    descriptionKey: "verification:status_verified_desc",
  },
  rejected: {
    label: "Rejected",
    description:
      "Previous verification submission could not be approved. Please review administrator notes on the verification page and resubmit updated documents.",
    badgeClass: "bg-red-50 text-red-800 border-red-300",
    dotClass: "bg-red-500",
    translationKey: "common:status.rejected",
    descriptionKey: "verification:status_rejected_desc",
  },
};

export const ACCOUNT_STATUS_CONFIG: Record<
  AccountStatus,
  { label: string; badgeClass: string }
> = {
  active: {
    label: "Active",
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-300",
  },
  restricted: {
    label: "Restricted",
    badgeClass: "bg-amber-50 text-amber-800 border-amber-300",
  },
  suspended: {
    label: "Suspended",
    badgeClass: "bg-red-50 text-red-800 border-red-300",
  },
  blocked: {
    label: "Blocked",
    badgeClass: "bg-red-50 text-red-800 border-red-300",
  },
  inactive: {
    label: "Inactive",
    badgeClass: "bg-slate-50 text-slate-700 border-slate-300",
  },
};

export const BUYER_TYPE_LABELS: Record<string, string> = {
  restaurant: "Restaurant / Dining",
  hotel: "Hotel / Hospitality",
  retailer: "Retailer / Supermarket",
  wholesaler: "Wholesaler / Distributor",
  food_processor: "Food Processor / Manufacturer",
  caterer: "Caterer / Institutional Kitchen",
  other: "Other Commercial Enterprise",
};

export interface ProfileCompletionInfo {
  percentage: number;
  completedCount: number;
  totalCount: number;
  missingFields: string[];
}

/**
 * Calculate profile completion percentage and identify missing recommended fields.
 */
export function calculateProfileCompletion(user: User): ProfileCompletionInfo {
  if (user.role === "farmer") {
    const profile = user.farmer_profile;
    const checks: { name: string; filled: boolean }[] = [
      { name: "Full Name", filled: Boolean(profile?.full_name?.trim()) },
      { name: "Farm Name", filled: Boolean(profile?.farm_name?.trim()) },
      { name: "Phone Number", filled: Boolean(user.phone_number?.trim()) },
      {
        name: "Farm Address",
        filled: Boolean(profile?.farm_location_address?.trim()),
      },
      { name: "City / Town", filled: Boolean(profile?.city?.trim()) },
      { name: "State / Province", filled: Boolean(profile?.state?.trim()) },
      { name: "Postal Code", filled: Boolean(profile?.postal_code?.trim()) },
      {
        name: "Cultivated Acres",
        filled:
          profile?.farm_size_acres !== undefined &&
          profile?.farm_size_acres !== null &&
          Number(profile.farm_size_acres) > 0,
      },
      {
        name: "Farming Practices",
        filled: Boolean(profile?.farming_practices?.trim()),
      },
      {
        name: "Primary Crops",
        filled: Boolean(profile?.primary_crops?.trim()),
      },
      { name: "Farm Bio / Overview", filled: Boolean(profile?.bio?.trim()) },
    ];

    const completedCount = checks.filter((c) => c.filled).length;
    const missingFields = checks.filter((c) => !c.filled).map((c) => c.name);
    const percentage = Math.round((completedCount / checks.length) * 100);

    return {
      percentage,
      completedCount,
      totalCount: checks.length,
      missingFields,
    };
  }

  if (user.role === "buyer") {
    const profile = user.buyer_profile;
    const checks: { name: string; filled: boolean }[] = [
      {
        name: "Contact Person Name",
        filled: Boolean(profile?.contact_person_name?.trim()),
      },
      {
        name: "Business / Trade Name",
        filled: Boolean(profile?.business_name?.trim()),
      },
      {
        name: "Commercial Entity Type",
        filled: Boolean(profile?.business_type?.trim()),
      },
      { name: "Contact Phone", filled: Boolean(user.phone_number?.trim()) },
      {
        name: "Business Registration / Tax ID",
        filled: Boolean(profile?.business_registration_number?.trim()),
      },
      {
        name: "Delivery Receiving Address",
        filled: Boolean(profile?.delivery_receiving_address?.trim()),
      },
      { name: "City", filled: Boolean(profile?.city?.trim()) },
      { name: "State / Province", filled: Boolean(profile?.state?.trim()) },
      { name: "Postal Code", filled: Boolean(profile?.postal_code?.trim()) },
      {
        name: "Procurement Requirements",
        filled: Boolean(profile?.procurement_summary?.trim()),
      },
      { name: "Business Bio / Narrative", filled: Boolean(profile?.bio?.trim()) },
    ];

    const completedCount = checks.filter((c) => c.filled).length;
    const missingFields = checks.filter((c) => !c.filled).map((c) => c.name);
    const percentage = Math.round((completedCount / checks.length) * 100);

    return {
      percentage,
      completedCount,
      totalCount: checks.length,
      missingFields,
    };
  }

  if (user.role === "transporter") {
    const profile = user.transporter_profile;
    const checks: { name: string; filled: boolean }[] = [
      {
        name: "Business Name",
        filled: Boolean(profile?.business_name?.trim()),
      },
      {
        name: "Contact Name",
        filled: Boolean(profile?.contact_name?.trim()),
      },
      {
        name: "Phone Number",
        filled: Boolean(profile?.phone_number?.trim() || user.phone_number?.trim()),
      },
      {
        name: "Vehicle Type",
        filled: Boolean(profile?.transport_type?.trim()),
      },
      {
        name: "Vehicle Registration",
        filled: Boolean(profile?.vehicle_registration_number?.trim()),
      },
      {
        name: "Payload Capacity",
        filled:
          profile?.vehicle_capacity_kg !== undefined &&
          profile?.vehicle_capacity_kg !== null &&
          Number(profile.vehicle_capacity_kg) > 0,
      },
      {
        name: "Operating States",
        filled: Boolean(profile?.operating_states?.trim()),
      },
      {
        name: "Experience Years",
        filled: profile?.experience_years !== undefined && profile?.experience_years !== null,
      },
      {
        name: "Fleet Overview / Bio",
        filled: Boolean(profile?.bio?.trim()),
      },
    ];

    const completedCount = checks.filter((c) => c.filled).length;
    const missingFields = checks.filter((c) => !c.filled).map((c) => c.name);
    const percentage = Math.round((completedCount / checks.length) * 100);

    return {
      percentage,
      completedCount,
      totalCount: checks.length,
      missingFields,
    };
  }

  return {
    percentage: 100,
    completedCount: 1,
    totalCount: 1,
    missingFields: [],
  };
}

export const SUBMISSION_STATUS_CONFIG: Record<
  string,
  { label: string; badgeClass: string; dotClass: string }
> = {
  pending: {
    label: "Under Review",
    badgeClass: "bg-blue-50 text-blue-800 border-blue-300",
    dotClass: "bg-blue-500",
  },
  approved: {
    label: "Approved",
    badgeClass: "bg-emerald-50 text-emerald-800 border-emerald-300",
    dotClass: "bg-emerald-500",
  },
  rejected: {
    label: "Rejected",
    badgeClass: "bg-red-50 text-red-800 border-red-300",
    dotClass: "bg-red-500",
  },
};

export const DOCUMENT_TYPE_LABELS: Record<string, string> = {
  // Farmer documents
  land_ownership: "Land Ownership Record / Title",
  kisan_credit_card: "Kisan Credit Card (KCC) / Farmer Passbook",
  government_id: "Government Photo Identification",
  organic_certification: "Organic / GAP Farming Certificate",
  // Buyer documents
  gstin_certificate: "GSTIN Registration Certificate",
  incorporation_certificate: "Certificate of Incorporation / Registration",
  fssai_license: "FSSAI Food Business License",
  trade_license: "Municipal Trade License / Shop & Est.",
  pan_card: "Commercial Entity PAN Card",
  // Transporter documents
  vehicle_rc: "Vehicle Registration Certificate (RC)",
  driving_license: "Commercial Driving License",
  transport_permit: "Commercial Goods Carriage Permit",
  business_registration: "Transport Agency Registration / GSTIN",
  insurance_certificate: "Commercial Vehicle Insurance Policy",
  fitness_certificate: "Vehicle Fitness Certificate",
  pollution_certificate: "Pollution Under Control (PUC) Certificate",
  // Common
  other: "Other Supporting Evidence",
};

export function getDocumentTypeLabel(type: string, t?: (key: string) => string): string {
  if (t) {
    const translated = t(`verification:doc_types.${type}`);
    if (translated && !translated.startsWith("verification:doc_types.")) {
      return translated;
    }
  }
  return DOCUMENT_TYPE_LABELS[type] || type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getLocalizedVerificationStatus(
  status: VerificationStatus,
  t?: (key: string) => string
): VerificationPresentation {
  const config = VERIFICATION_STATUS_CONFIG[status] || VERIFICATION_STATUS_CONFIG.unverified;
  if (!t) return config;
  return {
    ...config,
    label: t(config.translationKey) || config.label,
    description: t(config.descriptionKey) || config.description,
  };
}

export function getLocalizedAccountStatus(
  status: AccountStatus,
  t?: (key: string) => string
): { label: string; badgeClass: string } {
  const config = ACCOUNT_STATUS_CONFIG[status] || ACCOUNT_STATUS_CONFIG.active;
  if (!t) return config;
  return {
    ...config,
    label: t(`common:status.${status}`) || config.label,
  };
}

export function formatFileSize(bytes: number): string {
  if (bytes <= 0 || isNaN(bytes)) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const val = bytes / Math.pow(1024, i);
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}
