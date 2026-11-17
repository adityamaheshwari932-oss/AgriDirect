import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertTriangle, RefreshCw, Home } from "lucide-react";
import i18n from "../../i18n";

export interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode | ((error: Error, reset: () => void) => ReactNode);
  onReset?: () => void;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error,
    };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }

    // In development mode, log structured diagnostic details to the console
    if (import.meta.env?.DEV) {
      console.error("[ErrorBoundary caught an unhandled rendering error]:", error, errorInfo);
    }
  }

  public resetErrorBoundary = (): void => {
    if (this.props.onReset) {
      this.props.onReset();
    }
    this.setState({
      hasError: false,
      error: null,
    });
  };

  private handleReload = (): void => {
    if (typeof window !== "undefined") {
      window.location.reload();
    }
  };

  public render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (typeof this.props.fallback === "function") {
        return this.props.fallback(this.state.error, this.resetErrorBoundary);
      }

      if (this.props.fallback) {
        return this.props.fallback;
      }

      const isDev = Boolean(import.meta.env?.DEV);

      return (
        <div
          role="alert"
          aria-live="assertive"
          className="min-h-[50vh] flex items-center justify-center p-6 bg-background text-foreground"
        >
          <div className="max-w-lg w-full bg-card border border-border rounded-xl p-8 shadow-sm text-center space-y-6">
            <div className="mx-auto w-14 h-14 rounded-full bg-destructive/10 text-destructive flex items-center justify-center">
              <AlertTriangle className="w-8 h-8" aria-hidden="true" />
            </div>

            <div className="space-y-2">
              <h2 className="text-xl font-bold tracking-tight text-foreground">
                {i18n.t("errors:generic_title", "Something went wrong")}
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {i18n.t(
                  "errors:unexpected_error_desc",
                  "An unexpected technical error prevented this section of the application from displaying properly. Please try recovering or reloading the page."
                )}
              </p>
            </div>

            {isDev && this.state.error.message && (
              <div className="p-3 bg-secondary rounded-md text-left text-xs font-mono text-destructive overflow-x-auto max-h-36">
                <span className="font-semibold block mb-1">Error Message (Dev only):</span>
                {this.state.error.message}
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={this.resetErrorBoundary}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md bg-primary text-primary-foreground font-medium text-sm hover:bg-primary-700 transition-colors focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
              >
                <RefreshCw className="w-4 h-4" aria-hidden="true" />
                <span>{i18n.t("errors:try_again", "Try Again")}</span>
              </button>

              <button
                type="button"
                onClick={this.handleReload}
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md border border-border bg-card text-foreground font-medium text-sm hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <span>{i18n.t("common:actions.reload", "Reload Page")}</span>
              </button>

              <a
                href="/"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-4 py-2 rounded-md border border-border bg-card text-foreground font-medium text-sm hover:bg-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-primary"
              >
                <Home className="w-4 h-4" aria-hidden="true" />
                <span>{i18n.t("common:navigation.home", "Home")}</span>
              </a>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

