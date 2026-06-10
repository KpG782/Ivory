import App from "../src/App";
import { ErrorBoundary } from "../src/components/ErrorBoundary";

export default function Page() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
