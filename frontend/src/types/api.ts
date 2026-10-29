/**
 * API error response structures returned by FastAPI and Pydantic v2.
 */

export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

export interface ApiErrorResponse {
  detail?: string | ValidationErrorItem[];
}
