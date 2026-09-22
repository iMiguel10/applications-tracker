// shadcn (>= 4.2x) genera los componentes importando `cn` del paquete oficial `cn`
// (sustituto de clsx + tailwind-merge). Se reexporta aquí para que el código propio
// siga importando de "@/shared/lib/utils" y haya una única implementación.
export { cn } from "cn";
