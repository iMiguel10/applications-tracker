import { Button } from "@/shared/components/ui/button";

type FormActionsProps = {
  loading?: boolean;

  submitLabel: string;

  cancelLabel?: string;

  onCancel?: () => void;
};

export function FormActions({
  loading,
  submitLabel,
  cancelLabel,
  onCancel,
}: FormActionsProps) {
  return (
    <div className="flex justify-end gap-3 pt-6">

      {onCancel && (
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
        >
          {cancelLabel}
        </Button>
      )}

      <Button
        type="submit"
        disabled={loading}
      >
        {submitLabel}
      </Button>

    </div>
  );
}