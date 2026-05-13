// Register <json-video> web component as a valid JSX intrinsic element
declare namespace JSX {
  interface IntrinsicElements {
    "json-video": React.DetailedHTMLProps<
      React.HTMLAttributes<HTMLElement> & { src?: string },
      HTMLElement
    >;
  }
}
