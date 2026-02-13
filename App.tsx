
import React from 'react';
import { HashRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import Home from './pages/Home.tsx';
import Registration from './pages/Registration.tsx';
import Masterlist from './pages/Masterlist.tsx';
import PatientDetails from './pages/PatientDetails.tsx';

const Nav: React.FC = () => {
  const location = useLocation();
  const isHome = location.pathname === '/';

  if (isHome) return null;

  return (
    <nav className="bg-white border-b border-slate-200 px-6 py-4 flex justify-between items-center sticky top-0 z-50">
      <Link to="/" className="flex items-center gap-2 group">
        <div className="bg-emerald-600 p-1.5 rounded-lg text-white group-hover:bg-emerald-700 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path d="M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z" />
          </svg>
        </div>
        <span className="font-bold text-slate-800 tracking-tight text-lg">MEDICMISSION</span>
      </Link>
      <div className="flex gap-2 sm:gap-4">
        <Link 
          to="/registration" 
          className={`px-3 py-2 sm:px-4 rounded-full text-xs sm:text-sm font-semibold transition-all ${
            location.pathname === '/registration' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          REGISTRATION
        </Link>
        <Link 
          to="/masterlist" 
          className={`px-3 py-2 sm:px-4 rounded-full text-xs sm:text-sm font-semibold transition-all ${
            location.pathname === '/masterlist' ? 'bg-emerald-100 text-emerald-800' : 'text-slate-600 hover:bg-slate-100'
          }`}
        >
          MASTERLIST
        </Link>
      </div>
    </nav>
  );
};

const App: React.FC = () => {
  return (
    <Router>
      <div className="min-h-screen flex flex-col bg-slate-50">
        <Nav />
        <main className="flex-grow">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/registration" element={<Registration />} />
            <Route path="/masterlist" element={<Masterlist />} />
            <Route path="/patients/:id" element={<PatientDetails />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
};

export default App;
