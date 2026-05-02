const i={amp:"&",lt:"<",gt:">",quot:'"',apos:"'",nbsp:" "};function s(e){const t=String(e||"");if(typeof document<"u"){const r=document.createElement("textarea");return r.innerHTML=t,r.value}return t.replace(/&(#\d+|#x[\da-f]+|[a-z]+);/gi,(r,a)=>{const n=String(a||"").toLowerCase();return n.startsWith("#x")?String.fromCodePoint(parseInt(n.slice(2),16)):n.startsWith("#")?String.fromCodePoint(parseInt(n.slice(1),10)):i[n]??r})}function l(e){if(e==null)return"";let t=String(e).replace(/\r\n?/g,`
`).replace(/<script[\s\S]*?>[\s\S]*?<\/script>/gi,"").replace(/<style[\s\S]*?>[\s\S]*?<\/style>/gi,"");return/<\/?[a-z][\s\S]*>/i.test(t)&&(t=t.replace(/<br\s*\/?>/gi,`
`).replace(/<\/(p|div|section|article|header|footer|h[1-6]|tr)>/gi,`
`).replace(/<li[^>]*>/gi,"- ").replace(/<\/li>/gi,`
`).replace(/<\/?(ul|ol|table|tbody|thead|span|strong|b|em|i|font)[^>]*>/gi,"").replace(/<[^>]+>/g,"")),s(t).replace(/[ \t]+\n/g,`
`).replace(/\n{3,}/g,`

`).trim()}function c(e){return l(e).replace(/!\[([^\]]*)\]\([^)]+\)/g,"$1").replace(/\[([^\]]+)\]\([^)]+\)/g,"$1").replace(/^#{1,6}\s+/gm,"").replace(/(^|\s)([*_~`>]+)/g,"$1").replace(/[*_~`]+(\s|$)/g,"$1").replace(/\n{2,}/g," ").replace(/\s{2,}/g," ").trim()}export{c as m,l as n};
