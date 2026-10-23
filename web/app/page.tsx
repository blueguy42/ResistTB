import App from "@/components/App";
import { mockReport } from "@/lib/mock";

export default function Home() {
  return <App report={mockReport} />;
}
