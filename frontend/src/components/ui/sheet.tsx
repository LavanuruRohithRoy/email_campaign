import * as DialogPrimitive from "@radix-ui/react-dialog";

import { cn } from "@/lib/utils";

export const Sheet = DialogPrimitive.Root;
export const SheetTrigger = DialogPrimitive.Trigger;
export const SheetClose = DialogPrimitive.Close;
export const SheetContent = ({ className, ...props }: DialogPrimitive.DialogContentProps) => (
  <DialogPrimitive.Portal>
    <DialogPrimitive.Overlay className="fixed inset-0 z-50 bg-black/45" />
    <DialogPrimitive.Content className={cn("fixed inset-y-0 left-0 z-50 w-72 border-r bg-card p-4 shadow-lg", className)} {...props} />
  </DialogPrimitive.Portal>
);
