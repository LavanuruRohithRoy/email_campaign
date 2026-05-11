import * as AvatarPrimitive from "@radix-ui/react-avatar";

import { cn } from "@/lib/utils";

export const Avatar = ({ className, ...props }: AvatarPrimitive.AvatarProps) => (
  <AvatarPrimitive.Root className={cn("relative flex h-9 w-9 shrink-0 overflow-hidden rounded-full bg-muted", className)} {...props} />
);
export const AvatarImage = AvatarPrimitive.Image;
export const AvatarFallback = ({ className, ...props }: AvatarPrimitive.AvatarFallbackProps) => (
  <AvatarPrimitive.Fallback className={cn("flex h-full w-full items-center justify-center text-sm font-medium", className)} {...props} />
);
