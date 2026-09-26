export default function SpinnerOverlay({ visible, message }) {
  if (!visible) return null;

  return (
    <div className="spinner-overlay">
      <div className="spinner-box">
        <div className="spinner" />
        <p>{message}</p>
      </div>
    </div>
  );
}