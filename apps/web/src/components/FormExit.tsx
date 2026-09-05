import { useNavigate } from "react-router-dom";

type FormExitProps = {
  /** Where Cancel goes, and where the back arrow goes when history is empty. */
  fallback: string;
  /** Cream paper (public fill) vs dark desk chrome (builder). */
  variant?: "on-paper" | "on-dark";
};

function canGoBack() {
  const idx = (window.history.state as { idx?: number } | null)?.idx;
  return typeof idx === "number" && idx > 0;
}

export default function FormExit({ fallback, variant = "on-dark" }: FormExitProps) {
  const nav = useNavigate();

  const goBack = () => {
    if (canGoBack()) nav(-1);
    else nav(fallback);
  };

  const cancel = () => nav(fallback);

  return (
    <div className={`form-exit form-exit--${variant}`} data-demo="form-exit">
      <button
        type="button"
        className="form-exit-back"
        onClick={goBack}
        aria-label="Go back"
        data-demo="form-exit-back"
      >
        <span className="form-exit-arrow" aria-hidden="true" />
      </button>
      <button type="button" className="btn ghost form-exit-cancel" onClick={cancel} data-demo="form-exit-cancel">
        Cancel
      </button>
    </div>
  );
}
