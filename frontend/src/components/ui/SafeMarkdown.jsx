import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { normalizeMarkdownContent } from "../../utils/safeMarkdown";

const markdownComponents = {
  a: ({ children, href, ...props }) => (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-blue-700 underline underline-offset-2 hover:text-blue-800"
      {...props}
    >
      {children}
    </a>
  ),
  p: ({ children }) => <p className="m-0">{children}</p>,
  ul: ({ children }) => <ul className="m-0 list-disc space-y-1 pl-5">{children}</ul>,
  ol: ({ children }) => <ol className="m-0 list-decimal space-y-1 pl-5">{children}</ol>,
  li: ({ children }) => <li className="pl-1">{children}</li>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
};

export default function SafeMarkdown({ className = "", empty = "-", value }) {
  const normalized = normalizeMarkdownContent(value);

  if (!normalized) {
    return <span className="text-slate-400">{empty}</span>;
  }

  return (
    <div
      className={["space-y-2 text-sm leading-relaxed text-slate-700", className]
        .filter(Boolean)
        .join(" ")}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml components={markdownComponents}>
        {normalized}
      </ReactMarkdown>
    </div>
  );
}
