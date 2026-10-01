import {
  Bell,
  Briefcase,
  Building2,
  CalendarDays,
  FileText,
  IdCard,
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
  { to: "/calendar", labelKey: "nav.calendar", icon: CalendarDays },
  { to: "/documents", labelKey: "nav.documents", icon: FileText },
  { to: "/profile", labelKey: "nav.profile", icon: IdCard },
];
