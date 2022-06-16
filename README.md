# Benchmark for parallel ST_Union

## Description
The script runs `SELECT ST_Union(<column>) FROM <table>` or `SELECT
ST_Union(ST_Buffer(<column>, 0.001))` (with `--add-buffer`) query multiple times
and shows mean/median execution time.

`--before` argument is used to force parallel mode, see `before.sql`.

Test data used is USA admin boundaries from https://osm-boundaries.com with
`admin_level = 6`.

## Results (ms, mean/median)
### Forced parallel mode, on usa_6 (3258 records, full coverage with no overlapping).

* `SELECT ST_Union(wkb_geometry) FROM usa_6`

  No difference in execution time, small overhead for parallel version, but parallel mode
  is forced in this case:

| current               | test                 | current, parallel     | test, parallel        |
|-----------------------|----------------------|-----------------------|-----------------------|
| 6917.9835 / 6908.4755 | 6928.1752 / 6923.269 | 6912.3652 / 6913.9095 | 6955.4158 / 6954.5575 |

* `SELECT ST_Union(ST_Buffer(wkb_geometry, 0.001)) FROM usa_6`

  Parallel version is ~40% faster because `ST_Buffer` can be parallelized:

| current               | test                 | test, parallel        |
|-----------------------|----------------------|-----------------------|
| 9726.5593 / 9715.377  | 9737.2411 / 9731.438 | 5994.193 / 5982.6485  |

(see `result/` for more details)

## Usage

* `SELECT ST_Union(wkb_geometry) FROM usa_6`, forced parallel mode:

  ```
  $ ./bm.py --connection connection.json --table usa_6 --column wkb_geometry --times 10 --verbose --before before.sql
  ```

* `SELECT ST_Union(ST_Buffer(wkb_geometry, 0.001)) FROM usa_6`:

  ```
  $ ./bm.py --connection connection.json --table usa_6 --column wkb_geometry --times 10 --verbose --add-buffer`
  ```
