"use client";

import { useEffect } from "react";

/** Forwards "/" to the default language. Relative, so it also works under a GitHub Pages base path. */
export function RootRedirect({ target }: { target: string }) {
  useEffect(() => {
    window.location.replace(target);
  }, [target]);
  return null;
}
