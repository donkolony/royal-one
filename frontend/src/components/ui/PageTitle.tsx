import React from 'react';
import { Helmet } from 'react-helmet-async';

export function PageTitle({ title }: { title: string }) {
  return (
    <Helmet>
      <title>{title} | Royal Square Financial</title>
    </Helmet>
  );
}
