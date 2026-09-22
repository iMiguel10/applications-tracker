// F0: versión mínima. Se amplía en F2 con empresa, estado, fechas, etc.
export interface Application {
  id: string;
  position_title: string;
  company_name: string;
  created_at: string;
}

export interface ApplicationListParams {
  page: number;
  limit: number;
}
