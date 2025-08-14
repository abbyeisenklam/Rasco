#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <limits.h>
#include <assert.h>

#include "parsec_workload.h"

#ifdef _WIN32
#define DLL_EXPORT __declspec(dllexport)
#else
#define DLL_EXPORT
#endif

/**
 * This program is responsible for calculating theta values and
 * uploading both theta and phases into the litmus kernel for use
 * by DNA (From R. Gifford, N. Gandhi, L. T. X. Phan, and A. Haeberlen. DNA: Dynamic resource allocation for soft real-time multicore systems. In RTAS, 2021.)
 */

static void
_print_phase_entry(phase_entry_t *entry)
{
	if (entry == NULL) return;

	printf("Entry:\n");
	printf("\ttask_id: %u\n", entry->task_id);
	printf("\tphase_idx: %u\n", entry->phase_idx);
	printf("\tcache: %u\n", entry->cache);
	printf("\tmembw: %u\n", entry->membw);
	printf("\tinsn_start: %lu\n", entry->insn_start);
	printf("\tinsn_end: %lu\n", entry->insn_end);
	printf("\tinsn_rate: %lu\n", entry->insn_rate);
	printf("\tnext_entry: %p\n", entry->next_entry);

}

static phase_entry_t *
_delay_find_phase(phase_entry_t * (*all_res_phase_entries)[MAX_MEMBW_ITR], int (*all_res_phase_entries_len)[MAX_MEMBW_ITR],
		int task_id, int64_t insn, uint32_t cache, uint32_t membw)
{
	int64_t entry_start_insn, entry_end_insn;
	phase_entry_t *cur = NULL;
	int idx = 0;

	if (all_res_phase_entries == NULL || all_res_phase_entries_len == NULL) {
		printf("ERROR, all_res_phase_entries or all_res_phase_entries_len are NULL in delay_find_phase!\n");
		return NULL;
	}

	if (all_res_phase_entries[cache][membw] == NULL) {
		printf("ERROR, all_res_phase_entries at c: %d, b: %d is NULL!\n",
				cache, membw);
		return NULL;
	}

	for (idx = 0 ; idx < all_res_phase_entries_len[cache][membw] ; idx++) {

		cur = &all_res_phase_entries[cache][membw][idx];
		if (cur == NULL) {
			printf("ERROR, cur in delay_find_phase is NULL at index: %d\n", idx);
			return NULL;
		}

		if (cur->cache != cache || cur->membw != membw) {
			_print_phase_entry(cur);
			printf("ERROR, have mismatching caches or membws, cur_c: %d, c: %d, cur_m: %d, m: %d\n",
					cur->cache, cache, cur->membw, membw);
			return NULL;
		}

		entry_start_insn = cur->insn_start;
		entry_end_insn   = cur->insn_end;

		/* Did we find the right phase? */
		if (entry_start_insn <= insn && insn <= entry_end_insn) {
			assert(cur->insn_rate > 0);
			return cur;
		}
	}

	//printf("returning last phase from delay_find_phase.. target insn: %ld, end insn: %ld\n", insn, entry_end_insn);
	assert(cur->insn_rate > 0);
	return cur;
}

static int
_calc_theta(phase_entry_t * (*all_res_phase_entries)[MAX_MEMBW_ITR], int (*all_res_phase_entries_len)[MAX_MEMBW_ITR],
	    int task_id, uint64_t cur_insn, int cur_cache, int cur_membw,
	    int rem_cache, int rem_membw, phase_entry_t *cur_phase)
{
	int64_t cur_rate = 0;
	int64_t targ_rate = 0;
	int targ_cache = 0, targ_membw = 0;
	int count = 0;
	int64_t sum_diff = 0;
	phase_entry_t *targ_phase = NULL;

	if (cur_phase == NULL) {
		printf("ERROR, cur_phase NULL in _calc_theta\n");
		return -1;
	}

	//printf("\nCALCULATING THETA FOR PHASE WITH CUR_CACHE: %d, CUR_MEMBW: %d, INSN: %lu\n",
	//		cur_cache, cur_membw, cur_insn);
	//printf("theta value we are looking for is when rem_cache = %d and rem_membw = %d\n\n",
	//		rem_cache, rem_membw);

	cur_rate = cur_phase->insn_rate;
	//printf("CURRENT PHASE RATE: %ld\n", cur_rate);

	/* sum differences from current resource allocation up to remaining resouce allocation  */
	for (targ_cache = cur_cache ; targ_cache <= cur_cache + rem_cache ; targ_cache++) {
		for (targ_membw = cur_membw ; targ_membw <= cur_membw + rem_membw ; targ_membw++) {
			/* skip the edge case where we compare to ourselves */
			if (targ_cache == cur_cache && targ_membw == cur_membw) continue;

			/* Find the phase with increased resources */
			//printf("finding phase with insn: %lu, targ_cache: %d, targ_membw: %d\n",
			//		cur_insn, targ_cache, targ_membw);
			targ_phase = _delay_find_phase(all_res_phase_entries, all_res_phase_entries_len,
					task_id, cur_insn, targ_cache, targ_membw);

			if (targ_phase == NULL) {
				printf("ERROR, NULL in _calc_theta cur_c: %d, cur_m: %d, targ_c: %d, targ_m: %d, rem_c %d, rem_m: %d and insn is: %lu\n",
						cur_cache, cur_membw, targ_cache, targ_membw, rem_cache, rem_membw, cur_insn);
				continue;
			}

			targ_rate = targ_phase->insn_rate;
			if(targ_rate < 0) {
				printf("\tfound a phase, but rate is < 0?!\n");
				printf("\tfound, targ_cache: %d, targ_membw: %d, targ_insn_rate: %ld, cur_insn_rate: %ld, diff: %ld\n",
						targ_cache, targ_membw, targ_rate, cur_rate, targ_rate - cur_rate);
				assert(0);
			}
			//printf("\tfound, targ_cache: %d, targ_membw: %d, targ_insn_rate: %ld, cur_insn_rate: %ld, diff: %ld\n",
			//		targ_cache, targ_membw, targ_rate, cur_rate, targ_rate - cur_rate);

			if ((targ_rate - cur_rate) > 0) {
				sum_diff += targ_rate - cur_rate;
			} else {
				sum_diff += 1;
			}
			count++;
		}

	}

	if (count == 0) {
		cur_phase->theta_set[rem_cache][rem_membw].value = LONG_MIN;
		// printf("cur_c: %d, cur_m: %d, targ_c: %d, targ_m: %d, rem_c %d, rem_m: %d theta: %ld\n",
		// 		cur_cache, cur_membw, targ_cache, targ_membw, rem_cache, rem_membw,
		// 		cur_phase->theta_set[rem_cache][rem_membw].value);
		return 0;
	}

	// printf("final theta for phase when rem_cache: %d rem_membw: %d, with count: %d average, is: %ld\n",
	// 		rem_cache, rem_membw, count, sum_diff / count);
	//printf("saving it to this phase's theta_set for when rem_cache = %d and rem_membw = %d\n",
	//		rem_cache, rem_membw);

	cur_phase->theta_set[rem_cache][rem_membw].value = sum_diff / count;
	//printf("cur_c: %d, cur_m: %d, targ_c: %d, targ_m: %d, rem_c %d, rem_m: %d theta: %ld\n",
	//		cur_cache, cur_membw, targ_cache, targ_membw, rem_cache, rem_membw,
	//		cur_phase->theta_set[rem_cache][rem_membw].value);

	return 0;
}

/* -------- FUNCTIONS FOR PYTHON -------- */

phase_entry_t *canneal_all_res_phase_entries[MAX_CACHE_ITR][MAX_MEMBW_ITR];
int canneal_all_res_phase_entries_len[MAX_CACHE_ITR][MAX_MEMBW_ITR];

phase_entry_t *fft_all_res_phase_entries[MAX_CACHE_ITR][MAX_MEMBW_ITR];
int fft_all_res_phase_entries_len[MAX_CACHE_ITR][MAX_MEMBW_ITR];

phase_entry_t *streamcluster_all_res_phase_entries[MAX_CACHE_ITR][MAX_MEMBW_ITR];
int streamcluster_all_res_phase_entries_len[MAX_CACHE_ITR][MAX_MEMBW_ITR];

phase_entry_t *dedup_all_res_phase_entries[MAX_CACHE_ITR][MAX_MEMBW_ITR];
int dedup_all_res_phase_entries_len[MAX_CACHE_ITR][MAX_MEMBW_ITR];

DLL_EXPORT void
free_data() {
	for (int i = 0 ; i < MAX_CACHE_ITR ; i++) {
		for (int j = 0 ; j < MAX_MEMBW_ITR ; j++) {
			free(canneal_all_res_phase_entries[i][j]);
			free(fft_all_res_phase_entries[i][j]);
			free(streamcluster_all_res_phase_entries[i][j]);
			free(dedup_all_res_phase_entries[i][j]);
		}
	}
}

DLL_EXPORT phase_entry_t *get_phase_entries(size_t cache, size_t membw, enum task_name name)
{
	struct phase_parser *parser = NULL;
	phase_entry_t *(*all_res_phase_entries)[MAX_MEMBW_ITR];
	int (*all_res_phase_entries_len)[MAX_MEMBW_ITR];



	/* get a parser for the phase.txt file for this task, cache and membw combo */
	switch(name) {
		case CANNEAL: {
			parser = parsec_get_phase_parser(cache, membw, "canneal");
			all_res_phase_entries     = canneal_all_res_phase_entries;
			all_res_phase_entries_len = canneal_all_res_phase_entries_len;
			break;
		}
		case FFT: {
			parser = parsec_get_phase_parser(cache, membw, "fft");
			all_res_phase_entries     = fft_all_res_phase_entries;
			all_res_phase_entries_len = fft_all_res_phase_entries_len;
			break;
		}
		case STREAMCLUSTER: {
			parser = parsec_get_phase_parser(cache, membw, "streamcluster");
			all_res_phase_entries     = streamcluster_all_res_phase_entries;
			all_res_phase_entries_len = streamcluster_all_res_phase_entries_len;
			break;
		}
		case DEDUP: {
			parser = parsec_get_phase_parser(cache, membw, "dedup");
			all_res_phase_entries     = dedup_all_res_phase_entries;
			all_res_phase_entries_len = dedup_all_res_phase_entries_len;
			break;
		}
		default:
			printf("%d ERR, application type not handled\n", __LINE__);
			return NULL;
	}

	
	if (!parser) {
		printf("can't get parser for task: %d, cache: %ld, membw: %ld\n",
				name, cache, membw);
		return NULL;
	}

	assert(parser->num_phase_entries > 0);
	all_res_phase_entries[cache][membw] = (phase_entry_t *)malloc(sizeof(phase_entry_t) * parser->num_phase_entries);
	if (all_res_phase_entries[cache][membw] == NULL) {
		printf("Failed to allocate phase_entry_t array\n");
		parsec_free_parser(parser);
		return NULL;
	}
	// printf("task_id: %d, cache: %ld, membw: %ld, num phase entries: %d, num bytes for phase entries: %ld\n",
	// 		name, cache, membw, parser->num_phase_entries, sizeof(phase_entry_t) * parser->num_phase_entries);

	/* set all to 0 for now */
	memset(all_res_phase_entries[cache][membw], '\0', sizeof(phase_entry_t) * parser->num_phase_entries);
	all_res_phase_entries_len[cache][membw] = parser->num_phase_entries;

	int idx = 0, ret = 0;
	phase_entry_t *entry = &all_res_phase_entries[cache][membw][idx];
	phase_entry_t *prev_entry = NULL;
	entry->num_entries = parser->num_phase_entries;
	while (idx < parser->num_phase_entries && ((ret = parsec_get_next(parser, entry)) != EXIT_FAILURE)) {
		assert(parser->num_phase_entries > 0);
		if (prev_entry && ((entry->insn_start - prev_entry->insn_end) > 1)) {
			printf("for c %ld, bw: %ld\n", cache, membw);
			printf("diff prev_entry end: %lu, entry start: %lu, %lu\n",
				prev_entry->insn_end, entry->insn_start, entry->insn_start - prev_entry->insn_end);
			assert(0);
		}
		if (ret == 0) break;
		idx++;
		if (idx >= parser->num_phase_entries) break;
		prev_entry = entry;
		entry = &all_res_phase_entries[cache][membw][idx];
		entry->num_entries = parser->num_phase_entries;
		all_res_phase_entries[cache][membw][idx-1].next_entry = entry;
	}

	if (ret == EXIT_FAILURE) {
		parsec_free_parser(parser);
		free(all_res_phase_entries[cache][membw]);
		return NULL;
	}

	parsec_free_parser(parser);

	return all_res_phase_entries[cache][membw];

}

/* 
 * The goal of this function is to update the 'theta' and 'which' values for each phase entry
 * 	this requires that we find the asociated phase entry for each theta...
 */

DLL_EXPORT phase_entry_t *get_theta_entries(size_t cache, size_t membw, enum task_name name)
{
	int idx = 0;
	struct phase_parser *parser;
	phase_entry_t *(*all_res_phase_entries)[MAX_MEMBW_ITR];
	int (*all_res_phase_entries_len)[MAX_MEMBW_ITR];
	//printf("Calculating theta for this taskset wich cache: %ld, membw: %ld\n", cache, membw);

	/* get a parser for the theta.txt file for this task, cache and membw combo */
	switch(name) {
		case CANNEAL: {
			parser = parsec_get_theta_parser(cache, membw, "canneal");
			all_res_phase_entries     = canneal_all_res_phase_entries;
			all_res_phase_entries_len = canneal_all_res_phase_entries_len;
			break;
		}
		case FFT: {
			parser = parsec_get_theta_parser(cache, membw, "fft");
			all_res_phase_entries     = fft_all_res_phase_entries;
			all_res_phase_entries_len = fft_all_res_phase_entries_len;
			break;
		}
		case STREAMCLUSTER: {
			parser = parsec_get_theta_parser(cache, membw, "streamcluster");
			all_res_phase_entries     = streamcluster_all_res_phase_entries;
			all_res_phase_entries_len = streamcluster_all_res_phase_entries_len;
			break;
		}
		case DEDUP: {
			parser = parsec_get_theta_parser(cache, membw, "dedup");
			all_res_phase_entries     = dedup_all_res_phase_entries;
			all_res_phase_entries_len = dedup_all_res_phase_entries_len;
			break;
		}
		default:
			printf("%d ERR, application type not handled\n", __LINE__);
			return NULL;
	}

	//if (parsec_theta_exists(parser) == 1) {
	//	/* theta file is open for read only */
	//	phase_entry_t cur;
	//	int rem_cache;
	//	int rem_membw;
	//	while (parsec_read_theta(&cur, parser, &rem_cache, &rem_membw) == 0) {
	//		uint64_t targ_insn = (cur.insn_start + cur.insn_end) / 2;
	//		phase_entry_t *entry = _delay_find_phase(all_res_phase_entries, all_res_phase_entries_len, name,
	//						  						 targ_insn, cache, membw);
	//		if (!entry) {
	//			printf("ERROR, can't find phase entry during theta parse from file\n");
	//			return NULL;
	//		}
	//		unsigned int value = cur.theta_set[rem_cache][rem_membw].value;
	//		char which         = cur.theta_set[rem_cache][rem_membw].which;

	//		/* set thetas */
	//		entry->theta_set[rem_cache][rem_membw].value = value;
	//		entry->theta_set[rem_cache][rem_membw].which = which;
	//	}
	//	parsec_free_parser(parser);
	//	return all_res_phase_entries[cache][membw];

	//}

	if (parser == NULL) {
		printf("can't get parser for task: %s, cache: %ld, membw: %ld\n",
				"canneal", cache, membw);
		return NULL;
	}

	/* theta DOESN'T exist, calculate it! */
	//printf("THETA DOESN'T EXIST FOR C %ld, BW: %ld, CALCULATING, len of phase entires at this allocation: %d\n", cache, membw, all_res_phase_entries_len[cache][membw]);
	for (idx = 0 ; idx < all_res_phase_entries_len[cache][membw] ; idx++) {
		int rem_cache, rem_membw;
		uint64_t cur_insn = 0;

		//printf("Calculating theta for phase idx %d wich cache: %ld, membw: %ld\n", idx, cache, membw);

		phase_entry_t *cur_phase = &all_res_phase_entries[cache][membw][idx];
		if (cur_phase == NULL) {
			printf("ERROR, phase_entry NULL!\n");
			return NULL;
		}

		/* take the exact middle of our phase */
		cur_insn = (cur_phase->insn_start + cur_phase->insn_end) / 2;

		/* start by calculating theta for all possible remaining resource options */
		for (rem_cache     = (MAX_CACHE_ITR - 1) - cache ; rem_cache >= 0 ; rem_cache--) {
			for (rem_membw = (MAX_MEMBW_ITR - 1) - membw ; rem_membw >= 0 ; rem_membw--) {

				int ret = _calc_theta(all_res_phase_entries, all_res_phase_entries_len,
						name, cur_insn, cache,
						membw, rem_cache, rem_membw, cur_phase);
				if (ret) {
					return NULL;
				}
			}
		}

		/* Calculate 'which' */
		for (rem_cache     = (MAX_CACHE_ITR - 1) - cache ; rem_cache >= 0 ; rem_cache--) {
			for (rem_membw = (MAX_MEMBW_ITR - 1) - membw ; rem_membw >= 0 ; rem_membw--) {
				/* There is no theta if there is no remaining cache and membw */
				if (rem_cache == 0 && rem_membw == 0) continue;

				/* No cache left, just assign membw */
				if (rem_cache == 0) {
					cur_phase->theta_set[rem_cache][rem_membw].which = 1;
				} else if (rem_membw == 0) {
					cur_phase->theta_set[rem_cache][rem_membw].which = 0;

				/* normal case */
				} else if (cur_phase->theta_set[rem_cache][0].value > cur_phase->theta_set[0][rem_membw].value) {
					cur_phase->theta_set[rem_cache][rem_membw].which = 0;
				} else {
					cur_phase->theta_set[rem_cache][rem_membw].which = 1;
				}
				/* save that theta and entry to theta file for faster access later */
				if (parsec_write_theta(parser, cur_phase, rem_cache, rem_membw)) {
					printf("ERROR, failed to write theta to file\n");
					return NULL;
				}
			}
		}
	}
	parsec_free_parser(parser);

	return all_res_phase_entries[cache][membw];

}

DLL_EXPORT phase_entry_t *get_theta_sub_entries(size_t cache, size_t membw, enum task_name name, size_t idx)
{
	phase_entry_t *(*all_res_phase_entries)[MAX_MEMBW_ITR];
	switch(name) {
		case CANNEAL: {
			all_res_phase_entries = canneal_all_res_phase_entries;
			break;
		}
		case FFT: {
			all_res_phase_entries = fft_all_res_phase_entries;
			break;
		}
		case STREAMCLUSTER: {
			all_res_phase_entries = streamcluster_all_res_phase_entries;
			break;
		}
		case DEDUP: {
			all_res_phase_entries = dedup_all_res_phase_entries;
			break;
		}
		default:
			printf("%d ERR, application type not handled\n", __LINE__);
			return NULL;
	}
	return &all_res_phase_entries[cache][membw][idx];
}
/* ----- END OF PYTHON FUNCTIONS ----- */

int
main(int argc, char **argv)
{
	for (int c = 0 ; c < MAX_CACHE_ITR ; c++) {
		for (int bw = 0 ; bw < MAX_MEMBW_ITR ; bw++) {
			get_phase_entries(c, bw, FFT);
		}
	}
	for (int c = 0 ; c < MAX_CACHE_ITR ; c++) {
		for (int bw = 0 ; bw < MAX_MEMBW_ITR ; bw++) {
			get_theta_entries(c, bw, FFT);
		}
	}
	return 0;
}