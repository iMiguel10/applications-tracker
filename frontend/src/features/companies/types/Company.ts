export interface Company {
  id: string;
  name: string;
  website: string | null;
  location: string | null;
  notes: string | null;
  /** Solicitudes a esta empresa, incluidas las archivadas. */
  applications_count: number;
  created_at: string;
  updated_at: string;
}

export type CompanySort = "name" | "created_at" | "applications_count";

export interface CompanyListParams {
  page: number;
  limit: number;
  q?: string;
  sort_by?: CompanySort;
  order?: "asc" | "desc";
}
