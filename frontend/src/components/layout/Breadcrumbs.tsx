"use client";

import React from "react";
import Link from "next/link";
import { ChevronRight, Home } from "lucide-react";
import { useLanguage } from "../../context/LanguageContext";

export interface BreadcrumbItem {
  label: string;
  href?: string;
}

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
}

export const Breadcrumbs: React.FC<BreadcrumbsProps> = ({ items }) => {
  const { t } = useLanguage();

  return (
    <nav className="flex items-center space-x-1 text-xs text-gov-secondary py-3" aria-label="Breadcrumb">
      <Link href="/" className="flex items-center hover:text-primary transition-colors">
        <Home className="w-3.5 h-3.5 mr-1" />
        <span>{t("nav.home")}</span>
      </Link>
      {items.map((item, index) => (
        <React.Fragment key={index}>
          <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
          {item.href ? (
            <Link href={item.href} className="hover:text-primary transition-colors truncate max-w-xs">
              {item.label}
            </Link>
          ) : (
            <span className="font-medium text-gov-text truncate max-w-xs" aria-current="page">
              {item.label}
            </span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
};
