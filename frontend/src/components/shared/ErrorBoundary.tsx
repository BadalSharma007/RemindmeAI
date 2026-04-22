import { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error("ErrorBoundary caught an error:", error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div className="min-h-screen bg-background flex items-center justify-center px-6">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-error-container flex items-center justify-center mx-auto mb-6">
              <span className="text-2xl">⚠</span>
            </div>
            <h2 className="text-title-lg text-on-surface mb-3">Something went wrong</h2>
            <p className="text-body-md text-on-surface-variant mb-6">
              An unexpected error occurred. Please refresh the page or try again.
            </p>
            {this.state.error && (
              <p className="text-xs text-on-surface-variant/60 font-mono mb-6 bg-surface-container rounded-lg p-3">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={() => this.setState({ hasError: false, error: undefined })}
              className="btn-primary-gradient px-6 py-2.5 rounded-xl font-semibold text-sm"
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
