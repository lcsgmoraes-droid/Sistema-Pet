import { PawPrint } from "lucide-react";
import { resolveMediaUrl } from "../../utils/mediaUrl";

export default function PetAvatar({ alt = "Pet", className = "", name = "", size = "md", url }) {
  const imageUrl = resolveMediaUrl(url);
  const sizeClass =
    {
      sm: "h-9 w-9",
      md: "h-11 w-11",
      lg: "h-14 w-14",
    }[size] || "h-11 w-11";

  return (
    <div
      className={[
        "inline-flex shrink-0 items-center justify-center overflow-hidden rounded-lg border border-slate-200 bg-slate-100 text-slate-400",
        sizeClass,
        className,
      ]
        .filter(Boolean)
        .join(" ")}
      title={name || alt}
    >
      {imageUrl ? (
        <img src={imageUrl} alt={alt} className="h-full w-full object-cover" loading="lazy" />
      ) : (
        <PawPrint size={size === "lg" ? 24 : 18} aria-hidden="true" />
      )}
    </div>
  );
}
