import { lazy } from "react";
import { Route, Routes } from "react-router-dom";
import SiteLayout from "@/components/layout/SiteLayout";
import OnboardingOverlay from "@/components/onboarding/OnboardingOverlay";
import { OnboardingProvider } from "@/context/OnboardingContext";
import Home from "@/pages/Home";
import NotFound from "@/pages/NotFound";

const Booking = lazy(() => import("@/pages/Booking"));
const NovaAssistant = lazy(() => import("@/pages/NovaAssistant"));
const MyBookings = lazy(() => import("@/pages/MyBookings"));

export default function App() {
  return (
    <OnboardingProvider>
      <Routes>
        <Route element={<SiteLayout />}>
          <Route index element={<Home />} />
          <Route path="booking" element={<Booking />} />
          <Route path="nova" element={<NovaAssistant />} />
          <Route path="my-bookings" element={<MyBookings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
      <OnboardingOverlay />
    </OnboardingProvider>
  );
}
