
import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Patient } from '../types';
import { api } from '../api';

const PatientDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      if (!id) return;
      try {
        const data = await api.getPatient(parseInt(id));
        setPatient(data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [id]);

  if (loading) return <div className="p-20 text-center text-slate-400">Loading Patient Details...</div>;
  if (!patient) return <div className="p-20 text-center text-red-500">Patient not found.</div>;

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8 space-y-8">
      <div className="flex items-center gap-4">
        <Link to="/masterlist" className="p-2.5 rounded-2xl bg-white border border-slate-200 text-slate-400 hover:text-slate-600 transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
        </Link>
        <h1 className="text-2xl font-bold text-slate-800">Patient File: {patient.last_name}</h1>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <div className="md:col-span-1 space-y-6">
          <div className="bg-white p-2 rounded-3xl shadow-sm border border-slate-100 overflow-hidden">
            <img 
              src={api.getImageUrl(patient.id_image_path)} 
              alt="ID Document" 
              className="w-full h-auto rounded-2xl object-cover aspect-[3/4]"
            />
          </div>
          <div className="bg-slate-900 p-6 rounded-3xl text-white shadow-xl">
             <div className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-1">PhilHealth ID</div>
             <div className="text-xl font-mono tracking-wider">{patient.philhealth_no}</div>
          </div>
        </div>

        <div className="md:col-span-2 space-y-6">
          <div className="bg-white p-8 rounded-3xl shadow-sm border border-slate-100 space-y-8">
            <section className="grid grid-cols-2 gap-y-8">
              <div className="col-span-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-1">Full Name</label>
                <p className="text-2xl font-bold text-slate-800">{patient.first_name} {patient.middle_name} {patient.last_name}</p>
              </div>
              
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-1">Birth Date</label>
                <p className="text-lg font-semibold text-slate-700">{patient.birth_date}</p>
              </div>
              
              <div>
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-1">Sex</label>
                <p className="text-lg font-semibold text-slate-700">{patient.sex}</p>
              </div>

              <div className="col-span-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-1">Contact Details</label>
                <p className="text-lg font-semibold text-slate-700">{patient.contact_no || 'N/A'}</p>
              </div>

              <div className="col-span-2">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest block mb-1">Home Address</label>
                <p className="text-lg font-semibold text-slate-700 leading-relaxed">{patient.address}</p>
              </div>
            </section>

            <div className="pt-8 border-t border-slate-100 flex items-center justify-between">
              <div>
                 <span className="text-xs text-slate-400 font-medium">Record ID: #{patient.id}</span>
                 <p className="text-xs text-slate-400 font-medium">Captured: {new Date(patient.created_at!).toLocaleString()}</p>
              </div>
              <button className="px-6 py-2.5 bg-slate-100 text-slate-600 rounded-xl font-bold hover:bg-slate-200 transition-colors">
                PRINT SLIP
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PatientDetails;
