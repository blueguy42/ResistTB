import App from "@/components/App";
import { loadReport } from "@/lib/report";

export default function Home() {
  return <App report={loadReport()} />;
}
