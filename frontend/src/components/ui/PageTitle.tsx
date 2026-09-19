import React from 'react';
import { Helmet } from 'react-helmet-async';

const SUFFIX = 'Royal Square Financial';

/**
 * Sets the browser tab title ("<title> | Royal Square Financial") and renders nothing on the page.
 * Put your own visible <h1> in the page; do not repeat the suffix there.
 */
export function PageTitle({ title }: { title: string }) {
  // One string child: Helmet ignores a <title> whose children are an array ({title} | Suffix).
  return (
    <Helmet>
      <title>{`${title} | ${SUFFIX}`}</title>
    </Helmet>
  );
}
