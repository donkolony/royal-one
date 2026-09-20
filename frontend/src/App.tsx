import { Router } from "./router";
import DevLoginBanner from "./components/dev/DevLoginBanner";

export default function App() {
  return (
    <>
      <Router />
      <DevLoginBanner />
    </>
  );
}
