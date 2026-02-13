
import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { CameraStatus, Patient, OCRResponse } from '../types.ts';
import { api } from '../api.ts';

const ConfidenceBadge: React.FC<{ confidence: number }> = ({ confidence }) => {
  const isHigh = confidence >= 0.8;
  return (
    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${isHigh ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
      {isHigh ? '✓ HIGH' : '! LOW'}
    </span>
  );
};

const Registration: React.FC = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<CameraStatus>(CameraStatus.READY);
  const [isProcessing, setIsProcessing] = useState(false);
  const [capturedImage, setCapturedImage] = useState<string | null>(null);
  const [formData, setFormData] = useState<Patient>({
    philhealth_no: '',
    last_name: '',
    first_name: '',
    middle_name: '',
    birth_date: '',
    sex: '',
    address: '',
    contact_no: '',
    id_image_path: '',
  });
  const [ocrConfidences, setOcrConfidences] = useState<Record<string, number>>({});

  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  const startCamera = async () => {
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'environment'
        } 
      });
      if (videoRef.current) {
        videoRef.current.srcObject = mediaStream;
        setStream(mediaStream);
        setStatus(CameraStatus.ON);
      }
    } catch (err) {
      alert("Could not access camera. Please check permissions.");
    }
  };

  const capture = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    setIsProcessing(true);
    setStatus(CameraStatus.PROCESSING);
    
    const context = canvasRef.current.getContext('2d');
    if (!context) return;
    
    canvasRef.current.width = videoRef.current.videoWidth;
    canvasRef.current.height = videoRef.current.videoHeight;
    context.drawImage(videoRef.current, 0, 0);
    
    canvasRef.current.toBlob(async (blob) => {
      if (blob) {
        try {
          const result: OCRResponse = await api.captureAndOCR(blob);
          
          setFormData(prev => ({
            ...prev,
            philhealth_no: result.fields.philhealth_no.value,
            last_name: result.fields.last_name.value,
            first_name: result.fields.first_name.value,
            middle_name: result.fields.middle_name.value,
            birth_date: result.fields.birth_date.value,
            sex: result.fields.sex.value,
            address: result.fields.address.value,
            id_image_path: result.image.stored_filename,
          }));

          setOcrConfidences({
            philhealth_no: result.fields.philhealth_no.confidence,
            last_name: result.fields.last_name.confidence,
            first_name: result.fields.first_name.confidence,
            middle_name: result.fields.middle_name.confidence,
            birth_date: result.fields.birth_date.confidence,
            sex: result.fields.sex.confidence,
            address: result.fields.address.confidence,
          });

          setCapturedImage(result.image.preview_url);
          
          // Stop camera after capture
          if (stream) {
            stream.getTracks().forEach(track => track.stop());
            setStream(null);
          }
          setStatus(CameraStatus.READY);
        } catch (error) {
          alert("OCR failed. Manual entry required.");
          setStatus(CameraStatus.READY);
        } finally {
          setIsProcessing(false);
        }
      }
    }, 'image/jpeg', 0.95);
  }, [stream]);

  const handleSave = async () => {
    try {
      await api.savePatient(formData);
      alert("Record Saved Successfully!");
      navigate('/masterlist');
    } catch (error) {
      alert("Error saving record.");
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-4 sm:p-6 lg:p-8 space-y-8">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-slate-800">New Registration</h1>
        <div className={`px-4 py-1.5 rounded-full text-xs font-bold ${
          status === CameraStatus.ON ? 'bg-green-100 text-green-700' : 
          status === CameraStatus.PROCESSING ? 'bg-amber-100 text-amber-700 animate-pulse' : 
          'bg-slate-100 text-slate-500'
        }`}>
          {status}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="space-y-4">
          <div className="relative aspect-[4/3] bg-slate-900 rounded-3xl overflow-hidden shadow-inner flex items-center justify-center border-4 border-white shadow-xl">
            {status === CameraStatus.READY && !capturedImage && (
              <div className="text-center p-8">
                <div className="bg-slate-800 w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                  </svg>
                </div>
                <p className="text-slate-500 font-medium">Camera Offline</p>
                <button onClick={startCamera} className="mt-4 px-6 py-2.5 bg-emerald-600 text-white rounded-xl font-bold shadow-lg shadow-emerald-900/20 hover:bg-emerald-700 transition-all active:scale-95">
                  INITIALIZE CAMERA
                </button>
              </div>
            )}

            {status !== CameraStatus.READY && (
              <>
                <video ref={videoRef} autoPlay playsInline className="w-full h-full object-cover" />
                <div className="absolute inset-0 border-[40px] border-black/30 pointer-events-none">
                   <div className="w-full h-full border-2 border-dashed border-emerald-400/50 rounded-lg"></div>
                </div>
              </>
            )}

            {capturedImage && status === CameraStatus.READY && (
              <img src={api.getImageUrl(formData.id_image_path)} alt="Captured ID" className="w-full h-full object-cover" />
            )}

            {isProcessing && (
              <div className="absolute inset-0 bg-slate-900/60 flex flex-col items-center justify-center text-white backdrop-blur-sm">
                <div className="w-12 h-12 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-4"></div>
                <p className="font-bold tracking-widest text-sm">PROCESSING OCR...</p>
              </div>
            )}
          </div>

          <div className="flex gap-4">
            {status === CameraStatus.ON && (
              <button 
                onClick={capture}
                disabled={isProcessing}
                className="flex-1 py-4 bg-emerald-600 text-white rounded-2xl font-bold shadow-lg shadow-emerald-200 transition-all active:scale-[0.98] disabled:opacity-50"
              >
                CAPTURE PHOTO
              </button>
            )}
            {capturedImage && (
              <button 
                onClick={startCamera}
                className="flex-1 py-4 bg-slate-200 text-slate-700 rounded-2xl font-bold transition-all active:scale-[0.98]"
              >
                RETAKE PHOTO
              </button>
            )}
          </div>
          <canvas ref={canvasRef} className="hidden" />
        </div>

        <div className="bg-white p-6 rounded-3xl shadow-sm border border-slate-100 space-y-6">
          <h3 className="text-lg font-bold text-slate-700 border-b pb-3">Patient Information</h3>
          
          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">PhilHealth Number</label>
                {ocrConfidences.philhealth_no !== undefined && <ConfidenceBadge confidence={ocrConfidences.philhealth_no} />}
              </div>
              <input 
                value={formData.philhealth_no}
                onChange={e => setFormData({...formData, philhealth_no: e.target.value})}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all font-mono"
                placeholder="00-000000000-0"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Last Name</label>
                  {ocrConfidences.last_name !== undefined && <ConfidenceBadge confidence={ocrConfidences.last_name} />}
                </div>
                <input 
                  value={formData.last_name}
                  onChange={e => setFormData({...formData, last_name: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                />
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">First Name</label>
                  {ocrConfidences.first_name !== undefined && <ConfidenceBadge confidence={ocrConfidences.first_name} />}
                </div>
                <input 
                  value={formData.first_name}
                  onChange={e => setFormData({...formData, first_name: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
               <div className="col-span-1">
                <div className="flex justify-between mb-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Sex</label>
                  {ocrConfidences.sex !== undefined && <ConfidenceBadge confidence={ocrConfidences.sex} />}
                </div>
                <select 
                  value={formData.sex}
                  onChange={e => setFormData({...formData, sex: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                >
                  <option value="">Select</option>
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                </select>
              </div>
              <div className="col-span-2">
                <div className="flex justify-between mb-1">
                  <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Birth Date</label>
                  {ocrConfidences.birth_date !== undefined && <ConfidenceBadge confidence={ocrConfidences.birth_date} />}
                </div>
                <input 
                  value={formData.birth_date}
                  onChange={e => setFormData({...formData, birth_date: e.target.value})}
                  className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                  placeholder="YYYY-MM-DD"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between mb-1">
                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Address</label>
                {ocrConfidences.address !== undefined && <ConfidenceBadge confidence={ocrConfidences.address} />}
              </div>
              <textarea 
                value={formData.address}
                onChange={e => setFormData({...formData, address: e.target.value})}
                rows={2}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all resize-none"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Contact Number</label>
              <input 
                value={formData.contact_no}
                onChange={e => setFormData({...formData, contact_no: e.target.value})}
                className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl focus:ring-2 focus:ring-emerald-500 outline-none transition-all"
                placeholder="09XXXXXXXXX"
              />
            </div>
          </div>
        </div>
      </div>

      <div className="sticky bottom-4 left-0 right-0 pt-4">
        <button 
          onClick={handleSave}
          disabled={!formData.last_name || !formData.first_name || isProcessing}
          className="w-full py-4 bg-slate-900 text-white rounded-2xl font-bold shadow-2xl shadow-slate-400 hover:bg-slate-800 transition-all active:scale-[0.99] disabled:opacity-50 flex items-center justify-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          SAVE & COMPLETE RECORD
        </button>
      </div>
    </div>
  );
};

export default Registration;
