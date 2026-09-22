import { useEffect, useState } from "react";
import { Search } from "lucide-react";

import { useDebounce } from "@/shared/hooks/useDebounce";
import { Input } from "@/shared/components/ui/input";

interface SearchInputProps {
  value: string;
  /** Se llama con retardo: no en cada tecla, sino al dejar de escribir. */
  onChange: (value: string) => void;
  placeholder?: string;
  delay?: number;
}

/**
 * Buscador con debounce. Sin él, cada tecla lanzaría una petición y, con la búsqueda
 * en la URL, crearía una entrada de historial por letra.
 */
export function SearchInput({ value, onChange, placeholder, delay = 300 }: SearchInputProps) {
  const [text, setText] = useState(value);
  const debounced = useDebounce(text, delay);

  // Si el valor externo cambia (p. ej. al navegar atrás o al quitar filtros), el
  // campo lo refleja. Se ajusta durante el render comparando con el valor anterior,
  // el patrón recomendado por React, en vez de un efecto que provoca un render extra.
  const [previousValue, setPreviousValue] = useState(value);
  if (value !== previousValue) {
    setPreviousValue(value);
    setText(value);
  }

  useEffect(() => {
    if (debounced !== value) onChange(debounced);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debounced]);

  return (
    <div className="relative w-full max-w-xs">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        type="search"
        value={text}
        onChange={(event) => setText(event.target.value)}
        placeholder={placeholder}
        className="pl-8"
      />
    </div>
  );
}
