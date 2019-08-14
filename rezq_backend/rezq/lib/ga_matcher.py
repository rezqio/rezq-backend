import logging
import random
from copy import deepcopy
from difflib import SequenceMatcher
from functools import lru_cache

from django.utils import timezone

logger = logging.getLogger(__name__)


MAX_GENERATIONS = 50

# DIVISIBLE BY TWO PLEASE
POPULATION_SIZE = 24

CROSSOVER_PROBABILITY = 0.60
MUTATION_PROBABILITY = 0.08


def sel_stochastic_universal_sampling(individuals, k):
    """
    ADAPTED FROM
    https://github.com/DEAP/deap/blob/bee19008cd64946615bcd5c86c8e5c2ff0f3ddd9/deap/tools/selection.py#L182

    LICENSE
    https://github.com/DEAP/deap/blob/bee19008cd64946615bcd5c86c8e5c2ff0f3ddd9/LICENSE.txt

    Select the *k* individuals among the input *individuals*.
    The selection is made by using a single random value to sample all of the
    individuals by choosing them at evenly spaced intervals. The list returned
    contains references to the input *individuals*.
    :param individuals: A list of individuals to select from.
    :param k: The number of individuals to select.
    :return: A list of selected individuals.
    This function uses the :func:`~random.uniform` function
    from the python base
    :mod:`random` module.
    """
    s_inds = sorted(individuals, key=lambda x: x[1], reverse=True)
    sum_fits = sum(ind[1] for ind in individuals)

    distance = sum_fits / float(k)
    start = random.uniform(0, distance)
    points = [start + i*distance for i in range(k)]

    chosen = []
    for p in points:
        i = 0
        sum_ = s_inds[i][1]
        while sum_ < p:
            i += 1
            sum_ += s_inds[i][1]
        chosen.append(s_inds[i])

    return chosen


def cx_uniform_partialy_matched(ind1, ind2, indpb):
    """
    ADAPTED FROM
    https://github.com/DEAP/deap/blob/bee19008cd64946615bcd5c86c8e5c2ff0f3ddd9/deap/tools/crossover.py#L133

    LICENSE
    https://github.com/DEAP/deap/blob/bee19008cd64946615bcd5c86c8e5c2ff0f3ddd9/LICENSE.txt

    Executes a uniform partially matched crossover (UPMX) on the input
    individuals. The two individuals are modified in place. This crossover
    expects :term:`sequence` individuals of indices, the result for any other
    type of individuals is unpredictable.
    :param ind1: The first individual participating in the crossover.
    :param ind2: The second individual participating in the crossover.
    :returns: A tuple of two individuals.
    Moreover, this crossover generates two children by matching
    pairs of values chosen at random with a probability of *indpb* in the two
    parents and swapping the values of those indexes. For more details see
    [Cicirello2000]_.
    This function uses the :func:`~random.random` and :func:`~random.randint`
    functions from the python base :mod:`random` module.
    .. [Cicirello2000] Cicirello and Smith, "Modeling GA performance for
       control parameter optimization", 2000.
    """
    size = min(len(ind1), len(ind2))
    p1, p2 = [0]*size, [0]*size

    # Initialize the position of each indices in the individuals
    for i in range(size):
        p1[ind1[i]] = i
        p2[ind2[i]] = i

    for i in range(size):
        if random.random() < indpb:
            # Keep track of the selected values
            temp1 = ind1[i]
            temp2 = ind2[i]
            # Swap the matched value
            ind1[i], ind1[p1[temp2]] = temp2, temp1
            ind2[i], ind2[p2[temp1]] = temp1, temp2
            # Position bookkeeping
            p1[temp1], p1[temp2] = p1[temp2], p1[temp1]
            p2[temp1], p2[temp2] = p2[temp2], p2[temp1]

    return ind1, ind2


def mut_shuffle_indexes(individual, indpb):
    """
    ADAPTED FROM
    https://github.com/DEAP/deap/blob/bee19008cd64946615bcd5c86c8e5c2ff0f3ddd9/deap/tools/mutation.py#L91

    LICENSE
    https://github.com/DEAP/deap/blob/bee19008cd64946615bcd5c86c8e5c2ff0f3ddd9/LICENSE.txt

    Shuffle the attributes of the input individual and return the mutant.
    The *individual* is expected to be a :term:`sequence`. The *indpb* argument
    is the probability of each attribute to be moved. Usually this mutation is
    applied on vector of indices.
    :param individual: Individual to be mutated.
    :param indpb: Independent probability for each attribute to be exchanged to
                  another position.
    :returns: A tuple of one individual.
    This function uses the :func:`~random.random` and :func:`~random.randint`
    functions from the python base :mod:`random` module.
    """
    size = len(individual)
    for i in range(size):
        if random.random() < indpb:
            swap_indx = random.randint(0, size - 2)
            if swap_indx >= i:
                swap_indx += 1
            individual[i], individual[swap_indx] = \
                individual[swap_indx], individual[i]

    return individual


def get_matchings(matched_critiques, critiquer_requests):
    """Match critiques to critiquers using permutation genetic algorithm

    Encoding:

    Let a solution encoding be X = [x1, x2, ..., xn]
    where   n is the total number of matchings to be made
                i.e.,
                n = len(matched_critiques_list) = len(critiquer_requests_list)
            and xi are non-repeating integers from [0, n]

    Then for each i, a pairing is made between
        matched_critiques_list[i] and critiquer_requests_list[X[i]]

    Inspired by:
    http://www.iaeng.org/IJAM/issues_v36/issue_1/IJAM_36_1_7.pdf
    """
    matched_critiques_list = list(matched_critiques)
    critiquer_requests_list = list(critiquer_requests)

    logger.info(
        'Running GA matching on %d resumes and %d critiquers',
        len(matched_critiques_list),
        len(critiquer_requests_list),
    )

    # Make lists equal length; None is no-op if matched
    if len(matched_critiques_list) < len(critiquer_requests_list):
        matched_critiques_list += [None] * (
            len(critiquer_requests_list) - len(matched_critiques_list)
        )
    elif len(critiquer_requests_list) < len(matched_critiques_list):
        critiquer_requests_list += [None] * (
            len(matched_critiques_list) - len(critiquer_requests_list)
        )

    # The current time in seconds since epoch
    now_ts = timezone.now().timestamp()

    @lru_cache()
    def similarity_ratio_of(l1, l2):
        """How "similar" are sequences l1 and l2? Order matters.
        """
        return SequenceMatcher(None, l1, l2).ratio()

    @lru_cache()
    def industries_string_to_tuple(industries):
        return tuple(industries.split(','))

    @lru_cache()
    def get_pair_fitness(matched_critique_idx, critiquer_request_idx):
        """Get the fitness of a single pair of matched_critique and
        critiquer_request

        Returns 0.0 if totally incompatibile => will not match no matter what
        """
        matched_critique = matched_critiques_list[matched_critique_idx]
        critiquer_request = critiquer_requests_list[critiquer_request_idx]

        # no-op's have no fitness
        if matched_critique is None or critiquer_request is None:
            return 0.0

        # Don't critique your own resume
        if matched_critique.resume.uploader == critiquer_request.critiquer:
            return 0.0

        # How similar are the industries?
        similarity_ratio = similarity_ratio_of(
            industries_string_to_tuple(matched_critique.resume.industries),
            industries_string_to_tuple(critiquer_request.industries),
        )

        # How old are these requests?
        matched_critique_age = (
            now_ts - matched_critique.created_on.timestamp()
        )
        critiquer_request_age = (
            now_ts - critiquer_request.created_on.timestamp()
        )

        # Waterloo multipliers
        waterloo_critiquee = 1.0
        waterloo_both = 1.0

        # If critiquee is a waterloo student
        if matched_critique.resume.uploader.waterloo_id is not None:
            waterloo_critiquee = 1.2

            # If both people are waterloo students
            if critiquer_request.critiquer.waterloo_id is not None:
                waterloo_both = 1.2

        return similarity_ratio * (
            matched_critique_age + critiquer_request_age
        ) * waterloo_critiquee * waterloo_both

    @lru_cache()
    def get_individual_fitness(individual):
        """Sums the fitness of each matching made by this individual solution
        """
        fitness = 0.0
        for matched_critique_idx in range(len(individual)):
            critiquer_request_idx = individual[matched_critique_idx]
            fitness += get_pair_fitness(
                matched_critique_idx, critiquer_request_idx,
            )

        return fitness

    if len(matched_critiques_list) == len(critiquer_requests_list) == 1:
        logger.info('Only matching 1 to 1. Not going to run GA.')
        individual = (0,)

        fitness = get_individual_fitness(individual)
        if fitness != 0.0:
            logger.info('Successful match when matching 1 to 1.')
            return [(matched_critiques_list[0], critiquer_requests_list[0])]
        else:
            logger.info('No match when matching 1 to 1.')
            return []

    # List[      tuple(    tuple( int ), float   ) ]
    # List[ individual( encoding( int ), fitness ) ]
    population = []

    # Best solution so far
    #      tuple(    tuple( int ), float   )
    # individual( encoding( int ), fitness )
    best_so_far = None

    # Initial population
    for i in range(POPULATION_SIZE):
        # Randomly shuffles indices
        individual = list(range(len(matched_critiques_list)))
        random.shuffle(individual)
        individual = tuple(individual)
        population.append((individual, get_individual_fitness(individual)))

        if best_so_far is None or population[i][1] > best_so_far[1]:
            best_so_far = population[i]

    for gen_num in range(MAX_GENERATIONS):
        logger.info(
            'Generation %d/%d: %f', gen_num, MAX_GENERATIONS, best_so_far[1],
        )

        random.shuffle(population)

        # Elitist
        children = [deepcopy(best_so_far)]

        # Baker's stochastic universal sampling
        parents = sel_stochastic_universal_sampling(
            population, POPULATION_SIZE,
        )

        for i in range(POPULATION_SIZE - 1):
            p1 = parents[i][0]
            p2 = parents[i + 1][0]

            # Uniform PMX
            c1, c2 = cx_uniform_partialy_matched(
                list(p1), list(p2), CROSSOVER_PROBABILITY,
            )

            # Shuffle mutation
            c1 = tuple(mut_shuffle_indexes(c1, MUTATION_PROBABILITY))
            c2 = tuple(mut_shuffle_indexes(c2, MUTATION_PROBABILITY))

            children.append((c1, get_individual_fitness(c1)))
            children.append((c2, get_individual_fitness(c2)))

        # Sort children by descending fitness
        children.sort(key=lambda x: x[1], reverse=True)

        if children[i][1] > best_so_far[1]:
            best_so_far = children[i]

        # Remove the last child, since there is always exactly
        # 1 more child than POPULATION_SIZE
        del children[-1]

        population = children

    logger.info(
        'Generation %d/%d: %f',
        MAX_GENERATIONS, MAX_GENERATIONS, best_so_far[1],
    )

    matchings = []

    for matched_critique_idx in range(len(best_so_far[0])):
        critiquer_request_idx = best_so_far[0][matched_critique_idx]

        # Skip if completely incompatibile
        if get_pair_fitness(
            matched_critique_idx, critiquer_request_idx,
        ) == 0.0:
            continue

        matched_critique = matched_critiques_list[matched_critique_idx]
        critiquer_request = critiquer_requests_list[critiquer_request_idx]

        matchings.append((matched_critique, critiquer_request))

    logger.info(
        'GA finished with %d matches from %d resumes and %d critiquers,' +
        ' over %d generations with best fitness of %f',
        len(matchings),
        len(matched_critiques_list),
        len(critiquer_requests_list),
        MAX_GENERATIONS,
        best_so_far[1],
    )

    return matchings
