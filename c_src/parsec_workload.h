/* Author: Robert Gifford <rgif@seas.upenn.edu> */
/* From R. Gifford, N. Gandhi, L. T. X. Phan, and A. Haeberlen. DNA: Dynamic resource allocation for soft real-time multicore systems. In RTAS, 2021.*/

#ifndef PARSEC_WORKLOAD_H
#define PARSEC_WORKLOAD_H

#define MAX_RES_LEN 13 /* 1048575_1440 is 12 chars */
#define MAX_TASK_NAME_LEN 255 /* arbitrary */


#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <unistd.h>
#include <stdint.h>

#define MAX_CACHE_ITR 20
#define MAX_MEMBW_ITR 20

typedef struct {
	long signed value;
	char which; /* 0 if cache, 1 if membw, -1 if neither */
} theta_t;

typedef struct phase_entry {
    uint32_t task_id;
    uint32_t phase_idx;

    uint32_t cache; /* 1 - 19 */
    uint32_t membw; /* 1 - 19 */

    uint64_t insn_start;
    uint64_t insn_end;

    uint64_t insn_rate; /* instructions per ms */
    uint64_t num_entries; /* instructions per ms */

    /**
     * Each tau has a set of theta values which are the average of differences
     * between this phase's rate and all other phase rates from our cache and
     * membw allocation up to the remaining number of cache and membw that can
     * be allocated
     */
    theta_t theta_set[MAX_CACHE_ITR][MAX_MEMBW_ITR];

    struct phase_entry *next_entry;
} phase_entry_t;

/* this enum is for the experiments */
enum task_name {
	DEDUP = 0,
	CANNEAL,
	FFT,
	STREAMCLUSTER,
	RADIOSITY,
	FREQMINE,
	FIELD,
	MATRIX,
	NEIGHBORHOOD,
	POINTER,
	TRANSITIVE,
	UPDATE_DIS,
	LATENCY,
	CANNEAL_T, // sub thread of canneal
	NUM_TASK_TYPES
};

char *profile_path = "./profiles";

struct phase_parser {
	FILE *phase_file;
	FILE *theta_file;
	int theta_mode; /* 1 for read 2 for write */
	int task_idx;
	int cache; /* 1-19 */
	int membw; /* 1-19 */
	int num_phase_entries;
};

//static void _print_entry(struct phase_entry *entry);
//static void
//_print_entry(struct phase_entry *entry)
//{
//	printf("Entry:\n");
//	printf("\ttask_id: %d\n", entry->task_id);
//	printf("\tphase_idx: %d\n", entry->phase_idx);
//	printf("\tcache: %d\n", entry->cache);
//	printf("\tmembw: %d\n", entry->membw);
//	printf("\tinsn_start: %ld\n", entry->insn_start);
//	printf("\tinsn_end: %ld\n", entry->insn_end);
//	printf("\tinsn_rate: %d\n", entry->insn_rate);
//}

static enum task_name
parsec_get_workload_id(char *name)
{
	int ret;

	if (name == NULL) return -1;

	if (!strcmp((const char *)name, "dedup")) {
		ret = DEDUP;
	} else if (!strcmp((const char *)name, "canneal")) {
		ret = CANNEAL;
	//} else if (!strcmp((const char *)name, "ferret")) {
	//	ret = FERRET;
	//} else if (!strcmp((const char *)name, "fluidanimate")) {
	//	ret = FLUIDANIMATE;
	// } else if (!strcmp((const char *)name, "freqmine")) {
	// 	ret = FREQMINE;
	//} else if (!strcmp((const char *)name, "facesim")) {
	//	ret = FACESIM;
	//} else if (!strcmp((const char *)name, "splash2x.barnes")) {
	//	ret = BARNES;
	} else if (!strcmp((const char *)name, "fft")) {
		ret = FFT;
	//} else if (!strcmp((const char *)name, "splash2x.fmm")) {
	//	ret = FMM;
	//} else if (!strcmp((const char *)name, "splash2x.ocean_cp")) {
	//	ret = OCEAN_CP;
	// } else if (!strcmp((const char *)name, "radiosity")) {
	// 	ret = RADIOSITY;
	//} else if (!strcmp((const char *)name, "splash2x.raytrace")) {
	//	ret = RAYTRACE;
	} else if (!strcmp((const char *)name, "streamcluster")) {
		ret = STREAMCLUSTER;
	//} else if (!strcmp((const char *)name, "vips")) {
	//	ret = VIPS;
	//} else if (!strcmp((const char *)name, "x264")) {
	//	ret = X264;
	//} else if (!strcmp((const char *)name, "blackscholes")) {
	//	ret = BLACKSCHOLES;
	//} else if (!strcmp((const char *)name, "spark_graphx_pagerank_part0")) {
	//	ret = SPARK_GRAPHX_PAGERANK_PART0;
	//} else if (!strcmp((const char *)name, "spark_graphx_pagerank_driver")) {
	//	ret = SPARK_GRAPHX_PAGERANK_DRIVER;
	} else {
		printf("%s task not supported\n", name);
		return -1;
	}

	return ret;
}

static struct phase_parser *
parsec_get_phase_parser(int cache_itr, int membw_itr, char *task_name)
{
	char cache_str[MAX_RES_LEN];
	char membw_str[MAX_RES_LEN];
	char res_str[MAX_RES_LEN];
	char chr;
	/* 3 for the forward slashes 1 for null character */
	char full_path_phases[strlen(profile_path) + MAX_TASK_NAME_LEN + MAX_RES_LEN + strlen("phases.txt") + 4];
	int cache, membw, i, task_idx, count_lines = 0;

	FILE *phase_file = NULL;

	memset(cache_str, 0, sizeof(cache_str));
	memset(membw_str, 0, sizeof(membw_str));
	memset(res_str,   0, sizeof(res_str));
	memset(full_path_phases, 0, sizeof(full_path_phases));

	cache = 1;
	for (i = 0 ; i <= cache_itr ; i++) {
		cache = cache | (1 << i);
	}
	sprintf(cache_str, "%d", cache);

	membw = (membw_itr * 72) + 72;
	sprintf(membw_str, "%d", membw);

	strcat(res_str, cache_str);
	strcat(res_str, "_");
	strcat(res_str, membw_str);

	strcat(full_path_phases, profile_path);
	strcat(full_path_phases, "/");
	strcat(full_path_phases, task_name);
	strcat(full_path_phases, "/");
	strcat(full_path_phases, res_str);
	strcat(full_path_phases, "/");
	strcat(full_path_phases, "phases.txt");

	//printf("Look for path: %s\n", full_path_phases);

	struct phase_parser *parser = (struct phase_parser *)malloc(sizeof(struct phase_parser));
	if (parser == NULL) return NULL;

	phase_file = fopen(full_path_phases, "r");
	if (phase_file == NULL) {
		//printf("%s, Failed to open phase file at dir: %s, %s\n", __func__, full_path_phases, strerror(errno));
		free(parser);
		return NULL;
	}

	/* find number of lines in file */
	chr = getc(phase_file);
	while (chr != EOF) {
		if (chr == '\n') {
			count_lines = count_lines + 1;
		}
        	chr = getc(phase_file);
        }
	parser->num_phase_entries = count_lines;
	/* set the read head back to start */
	if (fseek(phase_file, 0, SEEK_SET)) {
		printf("failed to set read head back to start, fseek error!\n");
		return NULL;
	}


	task_idx = parsec_get_workload_id(task_name);
	if (task_idx < 0) {
		printf("Task not supported: %s\n", task_name);
		return NULL;
	}

	parser->phase_file = phase_file;
	parser->theta_file = NULL;
	parser->cache      = cache_itr;
	parser->membw      = membw_itr;
	parser->task_idx   = task_idx;
	//printf("Getting parser for: %s\n", full_path);

	return parser;
}

static struct phase_parser *
parsec_get_theta_parser(int cache_itr, int membw_itr, char *task_name)
{
	char cache_str[MAX_RES_LEN];
	char membw_str[MAX_RES_LEN];
	char res_str[MAX_RES_LEN];
	/* 3 for the forward slashes 1 for null character */
	char full_path_theta[strlen(profile_path) + MAX_TASK_NAME_LEN + MAX_RES_LEN + strlen("theta.txt") + 4];
	int cache, membw, i;
	FILE *theta_file = NULL;

	memset(cache_str, 0, sizeof(cache_str));
	memset(membw_str, 0, sizeof(membw_str));
	memset(res_str,   0, sizeof(res_str));
	memset(full_path_theta, 0, sizeof(full_path_theta));

	cache = 1;
	for (i = 0 ; i <= cache_itr ; i++) {
		cache = cache | (1 << i);
	}
	sprintf(cache_str, "%d", cache);

	membw = (membw_itr * 72) + 72;
	sprintf(membw_str, "%d", membw);

	strcat(res_str, cache_str);
	strcat(res_str, "_");
	strcat(res_str, membw_str);

	strcat(full_path_theta, profile_path);
	strcat(full_path_theta, "/");
	strcat(full_path_theta, task_name);
	strcat(full_path_theta, "/");
	strcat(full_path_theta, res_str);
	strcat(full_path_theta, "/");
	strcat(full_path_theta, "theta.txt");

	//struct phase_parser *parser = (struct phase_parser *)malloc(sizeof(struct phase_parser));
	struct phase_parser *parser = parsec_get_phase_parser(cache_itr, membw_itr, task_name);
	if (parser == NULL) return NULL;

	/* try to see if the theta file currently exists or not */
	if( access(full_path_theta, F_OK ) != -1) {
		/* exists open for reading */
		//printf("opening EXISTING theta file for reading: %s\n", full_path_theta);
		theta_file = fopen(full_path_theta, "r");
		parser->theta_mode = 1;
	} else {
		/* doesn't exist, open for writing */
		//printf("creating NEW theta file: %s\n", full_path_theta);
		theta_file = fopen(full_path_theta, "w");
		parser->theta_mode = 2;
	}

	if (theta_file == NULL) {
		printf("%s, Failed to open theta file: %s\n", __func__, strerror(errno));
		parser->theta_mode = 0;
		fclose(parser->phase_file);
		free(parser);
		return NULL;
	}

	parser->theta_file = theta_file;
	//printf("Getting parser for: %s\n", full_path);

	return parser;
}

static int
parsec_free_parser(struct phase_parser *parser)
{
	if (parser->phase_file) fclose(parser->phase_file);
	if (parser->theta_file) fclose(parser->theta_file);
	free(parser);

	return 0;
}

/* Main functionality of this library, read in a phase from the file and parse into entry */
static int
parsec_get_next(struct phase_parser *parser, phase_entry_t *entry)
{
	int ret;
	uint32_t phase_idx;
	uint64_t insn_rate;
	double insn_rate_f;
	//uint64_t insn_start, insn_end;
	double insn_start, insn_end;

	ret = fscanf(parser->phase_file, "%u,%lf,%lf,%lf\n",
			&phase_idx, &insn_start, &insn_end, &insn_rate_f);

	if (ret == EOF) return 0;

	if (ret != 4) {
		printf("ERROR, parsec_get_next didn't read all values we wanted to, read: %d\n", ret);
		return EXIT_FAILURE;
	}

	insn_rate = (uint64_t)insn_rate_f;

	entry->task_id         = parser->task_idx;
	entry->cache           = parser->cache;
	entry->membw           = parser->membw;
	entry->phase_idx       = phase_idx;
	entry->insn_start      = (uint64_t)insn_start;
	entry->insn_end        = (uint64_t)insn_end;
	entry->insn_rate       = insn_rate;
	entry->next_entry      = NULL;

	assert(entry->insn_start >= 0);
	assert(entry->insn_end > 0);
	assert(entry->insn_rate > 0);

	return ret;
}

static int
parsec_write_theta(struct phase_parser *parser, phase_entry_t *entry,
		   int rem_cache, int rem_membw)
{
	//assert(0);

	if (parser == NULL || entry == NULL) {
		printf("ERROR, parser or entry are NULL in parsec_write_theta\n");
		return -1;
	}

	if (parser->theta_file == NULL) {
		printf("ERROR, theta_file is NULL, can not write\n");
		return -1;
	}

	fprintf(parser->theta_file, "%u, %u, %u, %u, %lu, %lu, %d, %d, %ld, %ld\n",
			entry->task_id,
			entry->phase_idx,
			entry->cache,
			entry->membw,
			entry->insn_start,
			entry->insn_end,
			rem_cache,
			rem_membw,
			entry->theta_set[rem_cache][rem_membw].value,
			entry->theta_set[rem_cache][rem_membw].which);

	return 0;
}

static int
parsec_read_theta(phase_entry_t *entry, struct phase_parser *parser, int *rem_cache_ret, int *rem_membw_ret)
{
	uint32_t task_id, phase_idx, cache, membw;
	uint64_t insn_start, insn_end;
	int rem_cache, rem_membw;
	long value;
	char which;
	int ret;

	if (parser == NULL || entry == NULL || parser->theta_file == NULL) {
		printf("ERROR, NULL param(s) in parsec_read_theta\n");
		return -1;
	}

	ret = fscanf(parser->theta_file, "%u, %u, %u, %u, %lu, %lu, %d, %d, %ld, %c\n",
			&task_id, &phase_idx, &cache, &membw, &insn_start, &insn_end,
			&rem_cache, &rem_membw, &value, &which);

	if (ret == EOF) return 1;

	if (ret != 10) {
		printf("ERROR, didn't read all values we wanted to, read: %d, in parsec_read_theta\n", ret);
		return EXIT_FAILURE;
	}

	entry->task_id = task_id;
	entry->phase_idx = phase_idx;
	entry->cache = cache;
	entry->membw = membw;
	entry->insn_start = insn_start;
	entry->insn_end = insn_end;
	entry->theta_set[rem_cache][rem_membw].value = value;
	entry->theta_set[rem_cache][rem_membw].which = which;
	*rem_cache_ret = rem_cache;
	*rem_membw_ret = rem_membw;

	printf("Theta Entry:\n");
	printf("\ttask_id: %d\n", entry->task_id);
	printf("\tphase_idx: %d\n", entry->phase_idx);
	printf("\tcache: %d\n", entry->cache);
	printf("\tmembw: %d\n", entry->membw);
	printf("\tinsn_start: %ld\n", entry->insn_start);
	printf("\tinsn_end: %ld\n", entry->insn_end);
	printf("\tvalue: %ld\n", entry->theta_set[rem_cache][rem_membw].value);
	printf("\twhich: %d\n", entry->theta_set[rem_cache][rem_membw].which);

	return 0;
}

static int
parsec_theta_exists(struct phase_parser *parser)
{
	if (parser == NULL || parser->theta_file == NULL) {
		printf("ERROR, parser or theta_file NULL in parsec_theta_exists\n");
		return 0;
	}

	//printf("mode: %d\n", parser->theta_mode);

	if (parser->theta_mode == 1) return 1;

	return 0;
}

#endif /* PARSEC_WORKLOAD_H */
