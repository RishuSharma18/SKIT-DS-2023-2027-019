import { useEffect, useRef, useState, type DragEvent, type FormEvent } from 'react';
import { AlertTriangle, Check, FileImage, LoaderCircle, RotateCcw, ScanLine, Upload, X } from 'lucide-react';
import { recognizePlate } from '../services/api';
import type { PlateOCRResult } from '../types';

const MAX_FILE_BYTES = 10 * 1024 * 1024;
const ACCEPTED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/bmp']);
const ACCEPTED_EXTENSIONS = new Set(['.jpg', '.jpeg', '.png', '.webp', '.bmp']);

function isSupportedImage(file: File): boolean {
  const extension = file.name.toLowerCase().match(/\.[^.]+$/)?.[0] || '';
  return ACCEPTED_TYPES.has(file.type.toLowerCase()) || ACCEPTED_EXTENSIONS.has(extension);
}

export default function PlateOCRPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [result, setResult] = useState<PlateOCRResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!file) {
      setPreviewUrl('');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const selectFile = (selected: File | undefined) => {
    if (!selected) return;
    if (!isSupportedImage(selected)) {
      setError('Choose a JPEG, PNG, WebP, or BMP image.');
      return;
    }
    if (selected.size > MAX_FILE_BYTES) {
      setError('Image exceeds the 10MB upload limit.');
      return;
    }
    setFile(selected);
    setResult(null);
    setError('');
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    selectFile(event.dataTransfer.files[0]);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file || busy) return;
    setBusy(true);
    setError('');
    setResult(null);
    try {
      setResult(await recognizePlate(file));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Plate OCR failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
    setError('');
    if (inputRef.current) inputRef.current.value = '';
  };

  return (
    <section className="ops-ocr-layout" aria-label="Number plate OCR">
      <article className="ops-panel ops-ocr-upload">
        <div className="ops-ocr-intro">
          <span className="ops-ocr-icon"><ScanLine size={21} /></span>
          <div>
            <h2>Recognize a plate photo</h2>
            <p>Upload a clear image with the number plate visible. This tool processes one photo and does not use the CCTV video feed.</p>
          </div>
        </div>

        <form onSubmit={submit}>
          <input
            ref={inputRef}
            className="ops-ocr-file-input"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/bmp,.jpg,.jpeg,.png,.webp,.bmp"
            onChange={(event) => selectFile(event.target.files?.[0])}
            aria-label="Choose a plate photo"
          />
          {!file ? (
            <div
              className={`ops-ocr-dropzone ${dragging ? 'dragging' : ''}`}
              onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
              onDragOver={(event) => event.preventDefault()}
              onDragLeave={(event) => { if (event.currentTarget === event.target) setDragging(false); }}
              onDrop={handleDrop}
            >
              <span className="ops-ocr-drop-icon"><FileImage size={24} /></span>
              <b>Drop a plate photo here</b>
              <small>JPEG, PNG, WebP, or BMP · up to 10MB</small>
              <button className="ops-button ops-button-quiet" type="button" onClick={() => inputRef.current?.click()}>
                <Upload size={15} />Browse image
              </button>
            </div>
          ) : (
            <div className="ops-ocr-preview">
              <img src={previewUrl} alt="Selected number plate upload preview" />
              <div className="ops-ocr-file-details">
                <b>{file.name}</b>
                <small>{(file.size / (1024 * 1024)).toFixed(2)} MB · preview only until you recognize it</small>
              </div>
              <button className="ops-icon-button" type="button" onClick={reset} disabled={busy} aria-label="Remove selected image">
                <X size={17} />
              </button>
            </div>
          )}

          {error && <div className="ops-ocr-error" role="alert"><AlertTriangle size={16} />{error}</div>}
          <div className="ops-ocr-actions">
            <button className="ops-button ops-button-quiet" type="button" onClick={reset} disabled={busy || (!file && !result && !error)}>
              <RotateCcw size={15} />Reset
            </button>
            <button className="ops-button ops-button-primary" type="submit" disabled={!file || busy}>
              {busy ? <LoaderCircle size={16} className="animate-spin" /> : <ScanLine size={16} />}
              {busy ? 'Recognizing…' : 'Recognize plate'}
            </button>
          </div>
        </form>
        <p className="ops-ocr-privacy">The image is sent to the local AI service for processing and is not saved by this workflow.</p>
      </article>

      <article className="ops-panel ops-ocr-result-panel" aria-live="polite">
        <div className="ops-ocr-result-heading">
          <span className="ops-eyebrow">MACHINE-GENERATED RESULT</span>
          {result && <span className={`ops-ocr-confidence ${result.is_low_confidence ? 'low' : 'good'}`}>{Math.round(result.confidence * 100)}% confidence</span>}
        </div>
        {!result ? (
          <div className="ops-ocr-empty"><ScanLine size={25} /><b>Recognition result will appear here</b><small>Choose a plate photo and select “Recognize plate”.</small></div>
        ) : result.plate_detected ? (
          <>
            <div className="ops-ocr-recognized"><span><Check size={16} />Plate-like text recognized</span><code>{result.raw_text || result.text}</code></div>
            {result.normalized_text && <div className="ops-ocr-normalized"><span>Normalized format (suggestion)</span><code>{result.normalized_text}</code></div>}
            {result.is_low_confidence && <p className="ops-ocr-review"><AlertTriangle size={15} />Low confidence: verify the characters against the photo before using this result.</p>}
            <p className="ops-ocr-disclaimer">OCR is an estimate, not identity verification. Confirm the plate visually.</p>
            {result.candidates.length > 1 && (
              <div className="ops-ocr-candidates">
                <b>Other OCR candidates</b>
                <ul>{result.candidates.slice(0, 5).map((candidate, index) => (
                  <li key={`${candidate.text}-${index}`}><code>{candidate.text}</code><span>{Math.round(candidate.confidence * 100)}%</span></li>
                ))}</ul>
              </div>
            )}
          </>
        ) : (
          <div className="ops-ocr-no-result">
            <AlertTriangle size={19} />
            <b>No plate format could be confirmed</b>
            <small>{result.error || 'Try a closer, sharper photo with the full plate in view.'}</small>
            {result.text && <div className="ops-ocr-unconfirmed"><span>Unconfirmed text read</span><code>{result.raw_text || result.text}</code></div>}
            {result.candidates.length > 0 && (
              <div className="ops-ocr-candidates">
                <b>Possible text (review manually)</b>
                <ul>{result.candidates.slice(0, 5).map((candidate, index) => (
                  <li key={`${candidate.text}-${index}`}><code>{candidate.text}</code><span>{Math.round(candidate.confidence * 100)}%</span></li>
                ))}</ul>
              </div>
            )}
          </div>
        )}
      </article>
    </section>
  );
}
