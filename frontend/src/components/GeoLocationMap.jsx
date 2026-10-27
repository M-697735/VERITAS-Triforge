import React from 'react';
import { MapPin, Globe, Server, Info, AlertTriangle } from 'lucide-react';

export default function GeoLocationMap({ layer4 }) {
  if (!layer4) return null;

  const { city, country, accuracy_radius_km, originating_ip, asn, asn_org, is_datacenter, infra_category, is_resolved = true, domain_age_days, registrar } = layer4;

  const displayIp = originating_ip || 'No origin IP';

  return (
    <div className="bg-[#111827] border border-slate-800 rounded-2xl p-6 space-y-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2.5">
          <Globe className="w-5 h-5 text-emerald-400" />
          <h3 className="text-sm font-bold text-white">Infrastructure Geolocation & ASN Analysis</h3>
        </div>

        <div className="flex items-center space-x-2">
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800">
            Simulated demo dataset
          </span>
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[11px] font-mono text-cyan-400">
            <Info className="w-3.5 h-3.5 text-cyan-400" />
            <span>{is_resolved ? (accuracy_radius_km ? `Estimated region (±${accuracy_radius_km} km)` : 'Estimated region') : 'Unresolved'}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        
        {/* Visual Accuracy Radius Circle Display */}
        <div className="md:col-span-2 bg-slate-950 border border-slate-800 rounded-xl p-5 relative overflow-hidden flex flex-col justify-between min-h-[160px]">
          {/* Subtle Radar Grid Background */}
          <div className="absolute inset-0 bg-[radial-gradient(#1E293B_1px,transparent_1px)] [background-size:16px_16px] opacity-40"></div>

          <div className="relative z-10 flex items-center justify-center py-4">
            {is_resolved ? (
              <div className="relative flex items-center justify-center">
                {/* Accuracy Radius Outer Circle */}
                <div className="w-28 h-28 rounded-full bg-cyan-500/10 border-2 border-dashed border-cyan-500/40 animate-pulse flex items-center justify-center">
                  {accuracy_radius_km != null && (
                    <span className="text-[10px] font-mono font-bold text-cyan-400 bg-slate-900/90 px-2 py-0.5 rounded border border-cyan-800">
                      ±{accuracy_radius_km} km Radius
                    </span>
                  )}
                </div>
                <div className="absolute w-3 h-3 rounded-full bg-cyan-400 ring-4 ring-cyan-500/30"></div>
              </div>
            ) : (
              <div className="text-center space-y-2 py-2">
                <div className="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 flex items-center justify-center mx-auto">
                  <AlertTriangle className="w-6 h-6" />
                </div>
                <p className="text-xs font-semibold text-amber-300">
                  Unresolved IP Origin (Offline Database Limit)
                </p>
                <p className="text-[11px] text-slate-400 max-w-md mx-auto">
                  {originating_ip
                    ? `No local database entry matched IP ${originating_ip}. Zero false claims policy: origin is flagged as unconfirmed rather than generating fake codes.`
                    : 'No originating IP found in Received headers. Layer marked uncertain.'}
                </p>
              </div>
            )}
          </div>

          <div className="relative z-10 flex items-center justify-between border-t border-slate-900 pt-3 text-xs">
            <div className="flex items-center space-x-2">
              <MapPin className="w-4 h-4 text-cyan-400" />
              <span className="font-bold text-white">
                {is_resolved ? `${city}, ${country}` : 'Unresolved'}
              </span>
            </div>
            <span className="text-[11px] font-mono text-amber-400 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-900">
              {is_resolved ? 'NON-PRECISE REGION ONLY' : 'OFFLINE UNRESOLVED'}
            </span>
          </div>
        </div>

        {/* Infrastructure Metadata Card */}
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3 font-mono text-xs flex flex-col justify-between">
          <div className="space-y-2">
            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">ASN Metadata</span>
            
            <div className="space-y-1.5 pt-1">
              <div>
                <span className="text-slate-500">Origin IP: </span>
                <span className="text-cyan-400 font-bold">{displayIp}</span>
              </div>
              <div>
                <span className="text-slate-500">ASN Number: </span>
                <span className="text-slate-200">{asn || 'Unresolved'}</span>
              </div>
              <div>
                <span className="text-slate-500">Provider: </span>
                <span className="text-slate-200 line-clamp-2 text-[11px]">{asn_org || 'Unresolved'}</span>
              </div>
              <div>
                <span className="text-slate-500">Domain Age: </span>
                <span className="text-slate-200">
                  {domain_age_days == null ? 'Unknown' : `${domain_age_days} days (${registrar || 'Registrar'})`}
                </span>
              </div>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800">
            <span className="text-slate-500 text-[10px]">Infra Category:</span>
            <div className="flex items-center space-x-2 mt-1">
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                !is_resolved ? 'bg-amber-950 text-amber-400 border border-amber-800' :
                is_datacenter ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
              }`}>
                {(infra_category || 'no_origin_ip').toUpperCase()}
              </span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
