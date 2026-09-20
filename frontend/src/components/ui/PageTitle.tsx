/** React 19 hoists title elements to the document head. */
export function PageTitle({ title }: { title: string }) {
  return <title>{title} | Royal Square Financial</title>;
}
