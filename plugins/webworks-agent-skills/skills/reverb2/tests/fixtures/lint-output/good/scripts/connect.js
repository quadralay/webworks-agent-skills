// connect.js stub for the lint-output fixture. The deploy-unit check reads which
// per-parcel chunks a build fetches from these push calls (mirrors the real
// Parcels.Add in connect.js), so this stub fetches all three: _ix.html, _lx.js,
// _sx.js. An older build that omits the _lx.js line makes that chunk optional.
Parcels.index.push({ id: param_parcel_id, url: parcel_directory_url + '_ix.html' });
Parcels.landmarks.push(parcel_directory_url + '_lx.js?v=' + GLOBAL_GENERATION_HASH);
Parcels.search.push(parcel_directory_url + '_sx.js?v=' + GLOBAL_GENERATION_HASH);
