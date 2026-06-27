export function ErrorNotice({ message }: { message: string }) {
  if (!message) return null;
  return <p className="error-notice">{message}</p>;
}
