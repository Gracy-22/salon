import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import BookingFlow from "@/pages/BookingFlow";
import StylistLogin from "@/pages/StylistLogin";
import StylistPortal from "@/pages/StylistPortal";
import OwnerLogin from "@/pages/OwnerLogin";
import OwnerDashboard from "@/pages/OwnerDashboard";
import CustomerLookup from "@/pages/CustomerLookup";
import CustomerManage from "@/pages/CustomerManage";
import LandingPage from "@/pages/LandingPage";
import BeautexaLanding from "@/pages/BeautexaLanding";
import PrivacyPolicy from "@/pages/PrivacyPolicy";
import UnifiedLogin from "@/pages/UnifiedLogin";
import CustomerDashboard from "@/pages/CustomerDashboard";
import ManagerDashboard from "@/pages/ManagerDashboard";

function App() {
  return (
    <div className="App min-h-screen bg-[#FAF9F6] text-stone-900 font-sans">
      <Toaster position="top-center" richColors />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<BeautexaLanding />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          <Route path="/salon" element={<LandingPage />} />
          <Route path="/book" element={<BookingFlow />} />
          <Route path="/login" element={<UnifiedLogin />} />
          <Route path="/customer" element={<CustomerDashboard />} />
          <Route path="/lookup" element={<CustomerLookup />} />
          <Route path="/manage" element={<CustomerManage />} />
          <Route path="/manage/:token" element={<CustomerManage />} />
          <Route path="/stylist" element={<StylistLogin />} />
          <Route path="/stylist/portal" element={<StylistPortal />} />
          <Route path="/owner" element={<OwnerLogin />} />
          <Route path="/owner/dashboard" element={<OwnerDashboard />} />
          <Route path="/manager/dashboard" element={<ManagerDashboard />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </div>
  );
}

export default App;
