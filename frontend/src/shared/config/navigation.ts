import {
  Bell,
  Briefcase,
  Building2,
  FileText,
  LayoutDashboard,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  labelKey: string;
  icon: LucideIcon;
}

// Un solo rol (especificación §3): sin filtrado de menús por rol, a diferencia de GestPro.
export const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", labelKey: "nav.dashboard", icon: LayoutDashboard },
  { to: "/applications", labelKey: "nav.applications", icon: Briefcase },
  { to: "/companies", labelKey: "nav.companies", icon: Building2 },
  { to: "/reminders", labelKey: "nav.reminders", icon: Bell },
  { to: "/documents", labelKey: "nav.documents", icon: FileText },
];
