import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import Login from './pages/Login';
import EngagementList from './pages/EngagementList';
import EngagementCreate from './pages/EngagementCreate';
import EngagementDashboard from './pages/EngagementDashboard';
import ReviewQueue from './pages/ReviewQueue';
import Results from './pages/Results';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />

        {/* Protected layout wrapping main pages */}
        <Route element={<AppLayout />}>
          <Route path="/" element={<EngagementList />} />
          <Route path="/engagements/new" element={<EngagementCreate />} />
          <Route path="/engagements/:id" element={<EngagementDashboard />} />
          <Route path="/review" element={<ReviewQueue />} />
          <Route path="/results" element={<Results />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
