import { ReactNode } from "react";
import { hasPermission } from "./auth";

type Props = {
  permission: string;
  children: ReactNode;
};

export function RequirePermission({ permission, children }: Props) {
  if (!hasPermission(permission)) {
    return null;
  }
  return <>{children}</>;
}
