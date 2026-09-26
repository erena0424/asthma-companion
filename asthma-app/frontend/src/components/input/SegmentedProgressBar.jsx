function SegmentedProgressBar({ numPage, numPages }) {
  return (
    <div className="progress-row" >
        {Array.from({ length: numPages }).map((_, segment) => (
        <div
            key={segment}
            className={
            segment <= numPage
                ? "progress-segment filled"
                : "progress-segment"
            }
        />
        ))}
    </div>

  );
}

export default SegmentedProgressBar;